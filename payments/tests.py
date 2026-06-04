from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from activation.models import License
from payments.models import Order
from payments.views import fulfill_paid_order


User = get_user_model()


class PaymentFulfillmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="password123",
        )
        self.order = Order.objects.create(
            user=self.user,
            package="club",
            amount=19900,
            status="pending",
            stripe_session_id="cs_test_123",
        )

    @patch("payments.views.send_mail")
    def test_fulfill_paid_order_sets_plan_and_creates_package_keys_once(self, send_mail):
        order, license, created = fulfill_paid_order(self.order)

        self.user.profile.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertEqual(self.user.profile.plan, "club")
        self.assertTrue(created)
        self.assertEqual(license.license_keys.count(), 5)
        send_mail.assert_called_once()

        _, same_license, created_again = fulfill_paid_order(self.order)

        self.assertFalse(created_again)
        self.assertEqual(same_license.pk, license.pk)
        self.assertEqual(License.objects.filter(order=self.order).count(), 1)
        self.assertEqual(license.license_keys.count(), 5)
        send_mail.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    @patch("payments.views.send_mail")
    def test_success_page_verifies_paid_session_before_rendering_plan(self, send_mail, retrieve):
        retrieve.return_value = {
            "id": "cs_test_123",
            "payment_status": "paid",
            "status": "complete",
            "metadata": {"order": str(self.order.id)},
        }

        self.client.force_login(self.user)
        response = self.client.get(
            reverse("success"),
            {"session_id": "cs_test_123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Club Package")
        self.order.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.user.profile.plan, "club")
        self.assertEqual(License.objects.get(order=self.order).license_keys.count(), 5)
        send_mail.assert_called_once()
