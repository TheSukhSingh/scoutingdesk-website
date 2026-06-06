from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from activation.models import LicenseActivity
from django.contrib.messages import get_messages

User = get_user_model()


class CustomLoginTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123"

        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password=self.password,
        )

    def test_successful_login(self):
        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        self.assertEqual(response.status_code, 302)

    def test_invalid_login_creates_activity(self):
        self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": "wrongpassword",
            }
        )

        self.assertTrue(
            LicenseActivity.objects.filter(
                action="login_failed"
            ).exists()
        )

    def test_account_locked_after_five_failures(self):
        for _ in range(5):
            self.client.post(
                "/accounts/login/",
                {
                    "login": self.user.email,
                    "password": "wrong",
                }
            )

        profile = self.user.profile
        profile.refresh_from_db()

        self.assertTrue(profile.is_locked)
        self.assertEqual(profile.failed_attempts, 5)

    def test_locked_account_rejects_login(self):
        profile = self.user.profile
        profile.is_locked = True
        profile.locked_until = timezone.now() + timedelta(minutes=10)
        profile.save()

        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        self.assertEqual(response.status_code, 302)

    def test_lock_expires(self):
        profile = self.user.profile
        profile.is_locked = True
        profile.failed_attempts = 5
        profile.locked_until = timezone.now() - timedelta(minutes=1)
        profile.save()

        self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        profile.refresh_from_db()

        self.assertFalse(profile.is_locked)
        self.assertEqual(profile.failed_attempts, 0)

    def test_successful_login_resets_failed_attempts(self):
        profile = self.user.profile
        profile.failed_attempts = 4
        profile.is_locked = False
        profile.save()

        self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        profile.refresh_from_db()

        self.assertEqual(profile.failed_attempts, 0)

    def test_global_rate_limit(self):
        for _ in range(20):
            LicenseActivity.objects.create(
                action="login_failed",
                device_id="login",
                ip_address="127.0.0.1",
            )

        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": "wrong",
            }
        )

        self.assertEqual(response.status_code, 302)

    def test_nonexistent_email(self):
        response = self.client.post(
            "/accounts/login/",
            {
                "login": "missing@test.com",
                "password": "wrong",
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            LicenseActivity.objects.filter(
                action="login_failed"
            ).exists()
        )

    def test_failed_attempts_auto_reset_after_cooldown(self):
        profile = self.user.profile
        profile.failed_attempts = 4
        profile.is_locked = True
        profile.locked_until = timezone.now() - timedelta(minutes=20)
        profile.last_failed_at = timezone.now() - timedelta(minutes=20)
        profile.save()

        self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        profile.refresh_from_db()

        self.assertEqual(profile.failed_attempts, 0)
        self.assertFalse(profile.is_locked)

    def test_locked_account_without_locked_until(self):
        profile = self.user.profile
        profile.is_locked = True
        profile.locked_until = None
        profile.save()

        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        self.assertEqual(response.status_code, 302)

    def test_get_login_page(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)

    def test_successful_login_clears_last_failed_at(self):
        profile = self.user.profile
        profile.last_failed_at = timezone.now()
        profile.failed_attempts = 3
        profile.save()

        self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            }
        )

        profile.refresh_from_db()

        self.assertIsNone(profile.last_failed_at)

    def test_lock_sets_locked_until(self):
        for _ in range(5):
            self.client.post(
                "/accounts/login/",
                {
                    "login": self.user.email,
                    "password": "wrong",
                }
            )

        profile = self.user.profile
        profile.refresh_from_db()

        self.assertTrue(profile.is_locked)
        self.assertIsNotNone(profile.locked_until)

    def test_global_rate_limit_message(self):
        for _ in range(20):
            LicenseActivity.objects.create(
                action="login_failed",
                device_id="login",
                ip_address="127.0.0.1"
            )

        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": "wrong",
            },
            follow=True
        )

        msgs = [
            m.message
            for m in get_messages(response.wsgi_request)
        ]

        self.assertTrue(
            any(
                "Too many login attempts" in m
                for m in msgs
            )
        )

    def test_locked_account_message(self):
        profile = self.user.profile
        profile.is_locked = True
        profile.locked_until = timezone.now() + timedelta(minutes=10)
        profile.save()

        response = self.client.post(
            "/accounts/login/",
            {
                "login": self.user.email,
                "password": self.password,
            },
            follow=True
        )

        msgs = [
            m.message
            for m in get_messages(response.wsgi_request)
        ]

        self.assertTrue(
            any(
                "Account locked" in m
                for m in msgs
            )
        )