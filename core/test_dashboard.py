from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from activation.utils import create_license
from core.dashboard import dashboard_context
from payments.models import Order

User = get_user_model()


class DashboardContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="pass123"
        )

        self.order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

        create_license(
            user=self.user,
            package="agency",
            order=self.order
        )

    def test_non_admin_path_returns_empty_context(self):
        request = self.factory.get("/")
        context = dashboard_context(request)

        self.assertEqual(context, {})

    def test_dashboard_context_contains_stats(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertIn("dashboard_stats", context)
        self.assertIn("revenue_chart", context)
        self.assertIn("license_chart", context)
        self.assertIn("recent_payments", context)

    def test_total_users_count(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            context["dashboard_stats"]["total_users"],
            1
        )

    def test_successful_orders_count(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            context["dashboard_stats"]["successful_orders"],
            1
        )

    def test_total_revenue(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            context["dashboard_stats"]["total_revenue"],
            99.0
        )

    def test_recent_payments_exists(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            len(context["recent_payments"]),
            1
        )

    def test_chart_lengths_are_7(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            len(context["revenue_chart"]["labels"]),
            7
        )

        self.assertEqual(
            len(context["license_chart"]["labels"]),
            7
        )

    def test_active_license_count(self):
        request = self.factory.get("/admin/")
        context = dashboard_context(request)

        self.assertEqual(
            context["dashboard_stats"]["active_licenses"],
            1
        )