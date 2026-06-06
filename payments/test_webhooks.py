from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from activation.models import License
from payments.models import Order

User = get_user_model()


class StripeWebhookTests(TestCase):

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

    @patch("payments.views.stripe.Webhook.construct_event")
    @patch("payments.views._send_activation_email")
    def test_checkout_session_completed_creates_license(
        self,
        mock_email,
        mock_construct
    ):

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "payment_status": "paid",
                    "metadata": {
                        "order": str(self.order.id)
                    }
                }
            }
        }

        response = self.client.post(
            "/payments/webhook/",
            data=b"{}", 
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
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
            License.objects.filter(
                order=self.order
            ).count(),
            1
        )

    @patch("payments.views.stripe.Webhook.construct_event")
    @patch("payments.views._send_activation_email")
    def test_duplicate_webhook_does_not_duplicate_license(
        self,
        mock_email,
        mock_construct
    ):

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "payment_status": "paid",
                    "metadata": {
                        "order": str(self.order.id)
                    }
                }
            }
        }

        mock_construct.return_value = event

        self.client.post(
            "/payments/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
        )

        self.client.post(
            "/payments/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
        )

        self.assertEqual(
            License.objects.count(),
            1
        )

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_invalid_webhook_returns_400(
        self,
        mock_construct
    ):

        mock_construct.side_effect = Exception()

        response = self.client.post(
            "/payments/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
        )

        self.assertEqual(
            response.status_code,
            400
        )

    @patch("payments.views.stripe.checkout.Session.list")
    @patch("payments.views.stripe.Webhook.construct_event")
    @patch("payments.views._send_activation_email")
    def test_charge_refunded_deactivates_license(
        self,
        mock_email,
        mock_construct,
        mock_list
    ):

        from payments.views import fulfill_paid_order

        fulfill_paid_order(self.order)

        mock_list.return_value.data = [{
            "metadata": {
                "order": str(self.order.id)
            }
        }]

        mock_construct.return_value = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "payment_intent": "pi_123"
                }
            }
        }

        response = self.client.post(
            "/payments/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        license_obj = License.objects.get(
            order=self.order
        )

        license_obj.refresh_from_db()

        self.assertFalse(
            license_obj.is_active
        )

    @patch("payments.views._send_activation_email")
    def test_multiple_fulfill_calls_create_single_license(
        self,
        mock_email
    ):

        from payments.views import fulfill_paid_order

        fulfill_paid_order(self.order)
        fulfill_paid_order(self.order)
        fulfill_paid_order(self.order)

        self.assertEqual(
            License.objects.count(),
            1
        )

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_unknown_webhook_event_returns_200(
        self,
        mock_construct
    ):

        mock_construct.return_value = {
            "type": "something.unknown",
            "data": {
                "object": {}
            }
        }

        response = self.client.post(
            "/payments/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="abc"
        )

        self.assertEqual(
            response.status_code,
            200
        )