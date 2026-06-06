# core/tests/test_views.py

import json
from unittest.mock import mock_open, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from activation.utils import create_license
from payments.models import Order

User = get_user_model()


class CoreViewsTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass123"
        )

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_terms_page(self):
        response = self.client.get("/terms/")
        self.assertEqual(response.status_code, 200)

    def test_cookie_page(self):
        response = self.client.get("/cookie/")
        self.assertEqual(response.status_code, 200)

    def test_privacy_page(self):
        response = self.client.get("/privacy/")
        self.assertEqual(response.status_code, 200)

    def test_download_page(self):
        response = self.client.get("/download/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_logged_in(self):
        self.client.force_login(self.user)

        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_get_profile_data_without_license(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/profile/")
        data = response.json()

        self.assertFalse(data["device_active"])
        self.assertIsNone(data["last_seen"])
        self.assertEqual(data["email"], self.user.email)

    def test_get_profile_data_with_license(self):
        order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

        license_obj = create_license(
            user=self.user,
            package="agency",
            order=order
        )

        key = license_obj.license_keys.first()
        key.device_id = "device123"
        key.save()

        self.client.force_login(self.user)

        response = self.client.get("/api/profile/")
        data = response.json()

        self.assertTrue(data["device_active"])

    def test_update_profile_success(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/profile/update/",
            data=json.dumps({
                "first_name": "John",
                "last_name": "Doe",
                "club": "Barcelona",
                "role": "Scout"
            }),
            content_type="application/json"
        )

        self.user.refresh_from_db()

        self.assertTrue(response.json()["success"])
        self.assertEqual(self.user.first_name, "John")
        self.assertEqual(self.user.profile.club, "Barcelona")

    def test_update_profile_invalid_method(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/profile/update/")

        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"],
            "Invalid request"
        )

    def test_update_profile_invalid_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/profile/update/",
            data="invalid-json",
            content_type="application/json"
        )

        self.assertFalse(response.json()["success"])

    @patch("core.views.os.path.exists")
    def test_download_app_file_not_found(self, mock_exists):
        mock_exists.return_value = False

        response = self.client.get("/download/app/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "File not found")

    @patch("core.views.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"abc")
    def test_download_app_file_exists(
            self,
            mock_file,
            mock_exists):

        mock_exists.return_value = True

        response = self.client.get("/download/app/")

        self.assertEqual(response.status_code, 200)