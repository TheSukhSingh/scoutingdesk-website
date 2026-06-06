from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import UserProfile, AuthActivity

User = get_user_model()


class UserProfileSignalTests(TestCase):
    def test_profile_created_automatically(self):
        user = User.objects.create_user(
            username="test",
            email="test@example.com",
            password="pass123",
        )

        self.assertTrue(
            UserProfile.objects.filter(user=user).exists()
        )

    def test_profile_defaults(self):
        user = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
        )

        profile = user.profile

        self.assertEqual(profile.failed_attempts, 0)
        self.assertFalse(profile.is_locked)
        self.assertIsNone(profile.plan)

    def test_user_profile_string(self):
        user = User.objects.create_user(
            username="user3",
            email="user3@example.com",
            password="pass123",
        )

        user.profile.plan = "agency"
        user.profile.save()

        self.assertEqual(
            str(user.profile),
            "user3@example.com - agency"
        )


class AuthActivityModelTests(TestCase):
    def test_auth_activity_string(self):
        user = User.objects.create_user(
            username="user4",
            email="user4@example.com",
            password="pass123",
        )

        activity = AuthActivity.objects.create(
            user=user,
            email=user.email,
            action="login_success"
        )

        self.assertEqual(
            str(activity),
            "user4@example.com - login_success"
        )

    def test_auth_activity_without_email(self):
        user = User.objects.create_user(
            username="user5",
            email="user5@example.com",
            password="pass123",
        )

        activity = AuthActivity.objects.create(
            user=user,
            action="login_failed"
        )

        self.assertIn(
            "login_failed",
            str(activity)
        )