from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from activation.models import License
from payments.models import Order
from payments.views import (
    _checkout_session_is_paid,
    _session_get,
    _session_metadata,
    fulfill_paid_order,
)

User = get_user_model()


class OrderModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="password123"
        )

    def test_create_order(self):
        order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900
        )

        self.assertEqual(order.status, "pending")
        self.assertEqual(order.package, "agency")

    def test_order_string(self):
        order = Order.objects.create(
            user=self.user,
            package="club",
            amount=19900,
            status="paid"
        )

        self.assertIn("club", str(order))
        self.assertIn("paid", str(order))


class PaymentFulfillmentTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="password123"
        )

        self.order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="pending"
        )

    @patch("payments.views._send_activation_email")
    def test_fulfill_paid_order_sets_plan_and_creates_package_keys_once(
        self,
        mock_email
    ):
        order, license_obj, created = fulfill_paid_order(self.order)

        self.assertTrue(created)

        order.refresh_from_db()

        self.assertEqual(order.status, "paid")

        self.user.profile.refresh_from_db()

        self.assertEqual(
            self.user.profile.plan,
            "agency"
        )

        self.assertEqual(
            license_obj.license_keys.count(),
            2
        )

        order2, license2, created2 = fulfill_paid_order(self.order)

        self.assertFalse(created2)

        self.assertEqual(
            License.objects.filter(order=self.order).count(),
            1
        )

        self.assertEqual(
            license2.id,
            license_obj.id
        )

    @patch("payments.views.stripe.checkout.Session.retrieve")
    @patch("payments.views._send_activation_email")
    def test_success_page_verifies_paid_session_before_rendering_plan(
        self,
        mock_email,
        mock_retrieve
    ):
        self.client.force_login(self.user)

        self.order.stripe_session_id = "sess_123"
        self.order.save()

        mock_retrieve.return_value = {
            "id": "sess_123",
            "payment_status": "paid",
            "metadata": {
                "order": str(self.order.id)
            }
        }

        response = self.client.get(
            "/payments/success/?session_id=sess_123"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            "paid"
        )

        self.assertEqual(
            len(response.context["license_keys"]),
            2
        )

        self.assertEqual(
            response.context["expected_key_count"],
            2
        )

        self.assertContains(response, "Download ScoutingDesk")
        self.assertContains(response, "SD-")


class BillingHistoryTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="password123"
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="password123"
        )

    def test_login_required(self):

        response = self.client.get(
            "/payments/billing-history/"
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_only_current_user_orders_returned(self):

        Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

        Order.objects.create(
            user=self.other_user,
            package="club",
            amount=19900,
            status="paid"
        )

        self.client.force_login(self.user)

        response = self.client.get(
            "/payments/billing-history/"
        )

        data = response.json()

        self.assertEqual(
            len(data["orders"]),
            1
        )

    def test_summary_values(self):

        Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

        Order.objects.create(
            user=self.user,
            package="player",
            amount=4900,
            status="paid"
        )

        self.client.force_login(self.user)

        response = self.client.get(
            "/payments/billing-history/"
        )

        summary = response.json()["summary"]

        self.assertEqual(
            summary["successful_payments"],
            2
        )

        self.assertEqual(
            summary["total_spent"],
            148.0
        )


class HelperTests(TestCase):

    def test_session_get_dict(self):

        session = {
            "id": "abc"
        }

        self.assertEqual(
            _session_get(session, "id"),
            "abc"
        )

    def test_session_get_object(self):

        obj = Mock()
        obj.id = "xyz"

        self.assertEqual(
            _session_get(obj, "id"),
            "xyz"
        )

    def test_session_metadata(self):

        session = {
            "metadata": {
                "order": "5"
            }
        }

        self.assertEqual(
            _session_metadata(session)["order"],
            "5"
        )

    def test_paid_session_detection(self):

        session = {
            "payment_status": "paid"
        }

        self.assertTrue(
            _checkout_session_is_paid(session)
        )

    def test_complete_session_detection(self):

        session = {
            "status": "complete"
        }

        self.assertTrue(
            _checkout_session_is_paid(session)
        )

    def test_unpaid_session_detection(self):

        session = {
            "payment_status": "unpaid"
        }

        self.assertFalse(
            _checkout_session_is_paid(session)
        )


class PaymentExtraTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="password123"
        )

    def test_cancel_page(self):
        self.client.force_login(self.user)

        response = self.client.get("/payments/cancel/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment cancelled")

    def test_success_without_session_id(self):
        self.client.force_login(self.user)

        response = self.client.get("/payments/success/")

        self.assertEqual(response.status_code, 200)

    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_success_with_invalid_stripe_session(self, mock_retrieve):

        import stripe

        self.client.force_login(self.user)

        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "bad",
            "session"
        )

        response = self.client.get(
            "/payments/success/?session_id=bad"
        )

        self.assertEqual(response.status_code, 200)

    def test_order_from_checkout_session_fallback_to_session_id(self):

        order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            stripe_session_id="sess_123"
        )

        from payments.views import _order_from_checkout_session

        session = {
            "id": "sess_123"
        }

        found = _order_from_checkout_session(session)

        self.assertEqual(found.id, order.id)

    def test_session_metadata_empty(self):

        from payments.views import _session_metadata

        self.assertEqual(
            _session_metadata({}),
            {}
        )

    def test_session_get_default(self):

        self.assertEqual(
            _session_get({}, "missing", "abc"),
            "abc"
        )

    @patch("payments.views._send_activation_email")
    def test_fulfill_paid_order_when_order_already_paid(
        self,
        mock_email
    ):

        order = Order.objects.create(
            user=self.user,
            package="player",
            amount=4900,
            status="paid"
        )

        order, license_obj, created = fulfill_paid_order(order)

        self.assertTrue(created)

        order2, license2, created2 = fulfill_paid_order(order)

        self.assertFalse(created2)

        self.assertEqual(
            license_obj.id,
            license2.id
        )

    def test_order_string_pending(self):

        order = Order.objects.create(
            user=self.user,
            package="player",
            amount=4900
        )

        self.assertIn(
            "pending",
            str(order)
        )