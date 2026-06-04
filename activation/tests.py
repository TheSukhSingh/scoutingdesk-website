from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from activation.admin import LicenseActivityAdmin
from activation.models import LicenseActivity
from activation.utils import create_license
from payments.models import Order


User = get_user_model()


class LicenseActivityAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-buyer",
            email="admin-buyer@example.com",
            password="password123",
        )
        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="superuser@example.com",
            password="password123",
        )
        self.order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid",
        )
        self.license = create_license(
            user=self.user,
            package="agency",
            order=self.order,
        )
        self.license_key = self.license.license_keys.first()
        self.activity = LicenseActivity.objects.create(
            license=None,
            license_key=self.license_key,
            action="activate",
            device_id="test-device",
            ip_address="127.0.0.1",
        )

    def test_license_activity_changelist_renders_with_key_only_activity(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/activation/licenseactivity/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-buyer@example.com")
        self.assertContains(response, "Agency Seat 1")

    def test_admin_display_methods_tolerate_missing_direct_license(self):
        model_admin = LicenseActivityAdmin(LicenseActivity, admin.site)
        request = RequestFactory().get("/admin/activation/licenseactivity/")
        request.user = self.superuser
        queryset = model_admin.get_queryset(request)
        activity = queryset.get(pk=self.activity.pk)

        self.assertEqual(model_admin.owner_email(activity), "admin-buyer@example.com")
        self.assertEqual(model_admin.license_key_label(activity), "Agency Seat 1")
        self.assertEqual(model_admin.package(activity), "Agency")
