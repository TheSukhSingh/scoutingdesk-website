# activation/tests.py

import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from activation.admin import LicenseActivityAdmin
from activation.models import (
    License,
    LicenseActivity,
    LicenseKey,
    PackageConfig,
)
from activation.utils import (
    create_license,
    deactivate_license_by_order_object,
)
from activation.views import hash_device
from payments.models import Order

User = get_user_model()


class BaseActivationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer@test.com",
            username="buyer@test.com",
            password="password123"
        )

        self.other_user = User.objects.create_user(
            email="other@test.com",
            username="other@test.com",
            password="password123"
        )

        self.order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

        self.license = create_license(
            user=self.user,
            package="agency",
            order=self.order
        )

        self.license_key = self.license.license_keys.first()


class UtilityTests(BaseActivationTestCase):

    def test_create_license_creates_license(self):
        self.assertEqual(License.objects.count(), 1)

    def test_agency_creates_two_keys(self):
        self.assertEqual(
            self.license.license_keys.count(),
            2
        )

    def test_deactivate_license_by_order(self):
        deactivate_license_by_order_object(self.order)

        self.license.refresh_from_db()
        self.license_key.refresh_from_db()

        self.assertFalse(self.license.is_active)
        self.assertFalse(self.license_key.is_active)

    def test_hash_device_is_deterministic(self):
        self.assertEqual(
            hash_device("abc"),
            hash_device("abc")
        )


class ActivationTests(BaseActivationTestCase):

    def activate(self, device="device1"):
        return self.client.post(
            "/api/license/activate/",
            data=json.dumps({
                "activation_key": self.license_key.key,
                "device_id": device
            }),
            content_type="application/json"
        )

    def test_activate_success(self):
        response = self.activate()

        self.assertTrue(response.json()["valid"])

    def test_activate_missing_data(self):
        response = self.client.post(
            "/api/license/activate/",
            data=json.dumps({}),
            content_type="application/json"
        )

        self.assertFalse(response.json()["valid"])

    def test_activate_invalid_key(self):
        response = self.client.post(
            "/api/license/activate/",
            data=json.dumps({
                "activation_key": "BADKEY",
                "device_id": "pc"
            }),
            content_type="application/json"
        )

        self.assertFalse(response.json()["valid"])

    def test_activate_binds_device(self):
        self.activate()

        self.license_key.refresh_from_db()

        self.assertIsNotNone(self.license_key.device_id)

    def test_same_device_can_reactivate(self):
        self.activate()

        response = self.activate()

        self.assertTrue(response.json()["valid"])

    def test_other_device_rejected(self):
        self.activate()

        response = self.activate("device2")

        self.assertFalse(response.json()["valid"])

    def test_inactive_license_rejected(self):
        self.license.is_active = False
        self.license.save()

        response = self.activate()

        self.assertFalse(response.json()["valid"])

    def test_session_token_created(self):
        self.activate()

        self.license_key.refresh_from_db()

        self.assertIsNotNone(self.license_key.session_token)


class ValidationTests(BaseActivationTestCase):

    def setUp(self):
        super().setUp()

        self.client.post(
            "/api/license/activate/",
            data=json.dumps({
                "activation_key": self.license_key.key,
                "device_id": "pc1"
            }),
            content_type="application/json"
        )

        self.license_key.refresh_from_db()

    def validate(self, token=None, device="pc1"):
        return self.client.post(
            "/api/license/validate/",
            data=json.dumps({
                "token": token or self.license_key.session_token,
                "device_id": device
            }),
            content_type="application/json"
        )

    def test_validate_success(self):
        response = self.validate()

        self.assertTrue(response.json()["valid"])

    def test_invalid_token(self):
        response = self.validate("badtoken")

        self.assertFalse(response.json()["valid"])

    def test_device_mismatch(self):
        response = self.validate(device="otherpc")

        self.assertFalse(response.json()["valid"])

    def test_expired_token(self):
        self.license_key.token_expires_at = timezone.now() - timedelta(days=1)
        self.license_key.save()

        response = self.validate()

        self.assertFalse(response.json()["valid"])

    def test_inactive_license_fails(self):
        self.license.is_active = False
        self.license.save()

        response = self.validate()

        self.assertFalse(response.json()["valid"])


class DashboardTests(BaseActivationTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_my_licenses(self):
        response = self.client.get("/api/license/my-licenses/")

        self.assertEqual(response.status_code, 200)

    def test_reset_device_success(self):
        self.license_key.device_id = "abc"
        self.license_key.save()

        response = self.client.post(
            "/api/license/reset-device/",
            data=json.dumps({
                "activation_key": self.license_key.key
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])

    def test_reset_device_wrong_user(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            "/api/license/reset-device/",
            data=json.dumps({
                "activation_key": self.license_key.key
            }),
            content_type="application/json"
        )

        self.assertFalse(response.json()["success"])

    def test_regenerate_key(self):
        old_key = self.license_key.key

        response = self.client.post(
            "/api/license/regenerate-key/",
            data=json.dumps({
                "activation_key": old_key
            }),
            content_type="application/json"
        )

        self.assertTrue(response.json()["success"])

        self.license_key.refresh_from_db()

        self.assertNotEqual(old_key, self.license_key.key)


class AdminTests(BaseActivationTestCase):

    def setUp(self):
        super().setUp()

        self.superuser = User.objects.create_superuser(
            email="admin@test.com",
            username="admin",
            password="password123"
        )

        self.activity = LicenseActivity.objects.create(
            license_key=self.license_key,
            action="activate",
            device_id="abc",
            ip_address="127.0.0.1"
        )

    def test_admin_methods(self):
        model_admin = LicenseActivityAdmin(
            LicenseActivity,
            admin.site
        )

        activity = LicenseActivity.objects.get(pk=self.activity.pk)

        self.assertEqual(
            model_admin.owner_email(activity),
            self.user.email
        )

        self.assertEqual(
            model_admin.package(activity),
            "Agency"
        )

from activation.admin import LicenseAdmin
from django.contrib import admin

class LicenseAdminActionTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="adminaction@test.com",
            username="adminaction",
            password="password"
        )

        self.order = Order.objects.create(
            user=self.user,
            package="player",
            amount=4900,
            status="paid"
        )

        self.license = create_license(
            self.user,
            "player",
            self.order
        )

    def test_activate_selected_action(self):
        self.license.is_active = False
        self.license.save()

        admin_obj = LicenseAdmin(License, admin.site)

        queryset = License.objects.all()

        admin_obj.activate_selected(
            None,
            queryset
        )

        self.license.refresh_from_db()

        self.assertTrue(
            self.license.is_active
        )

    def test_deactivate_selected_action(self):
        admin_obj = LicenseAdmin(
            License,
            admin.site
        )

        queryset = License.objects.all()

        admin_obj.deactivate_selected(
            None,
            queryset
        )

        self.license.refresh_from_db()

        self.assertFalse(
            self.license.is_active
        )