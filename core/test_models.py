from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserProfileSignalTests(TestCase):

    def test_profile_created_automatically(self):
        user = User.objects.create_user(
            email="signal@test.com",
            username="signal",
            password="password"
        )

        self.assertIsNotNone(
            user.profile
        )

    def test_profile_string(self):
        user = User.objects.create_user(
            email="profile@test.com",
            username="profile",
            password="password"
        )

        user.profile.plan = "agency"
        user.profile.save()

        self.assertIn(
            "profile@test.com",
            str(user.profile)
        )