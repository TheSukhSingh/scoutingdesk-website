from django.contrib.auth import get_user_model
from django.test import TestCase

from activation.models import (
    License,
    LicenseActivity,
    LicenseKey,
    PackageConfig,
)
from activation.utils import (
    create_license,
    get_package_license_count,
)
from payments.models import Order
from activation.models import generate_activation_key

User = get_user_model()


class PackageConfigTests(TestCase):
    def test_default_license_count_player(self):
        self.assertEqual(get_package_license_count("player"), 1)

    def test_default_license_count_agency(self):
        self.assertEqual(get_package_license_count("agency"), 2)

    def test_default_license_count_club(self):
        self.assertEqual(get_package_license_count("club"), 5)

    def test_unknown_package_defaults_to_one(self):
        self.assertEqual(get_package_license_count("unknown"), 1)

    def test_package_config_overrides_default(self):
        PackageConfig.objects.create(
            package="agency",
            max_licenses=7,
        )

        self.assertEqual(
            get_package_license_count("agency"),
            7,
        )


class LicenseModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            username="user",
            password="password"
        )

        self.order = Order.objects.create(
            user=self.user,
            package="agency",
            amount=9900,
            status="paid"
        )

    def test_create_license_creates_license(self):
        license = create_license(
            self.user,
            "agency",
            self.order
        )

        self.assertEqual(
            License.objects.count(),
            1
        )

        self.assertEqual(
            license.package,
            "agency"
        )

    def test_agency_creates_two_keys(self):
        license = create_license(
            self.user,
            "agency",
            self.order
        )

        self.assertEqual(
            license.license_keys.count(),
            2
        )

    def test_club_creates_five_keys(self):
        license = create_license(
            self.user,
            "club",
            self.order
        )

        self.assertEqual(
            license.license_keys.count(),
            5
        )

    def test_player_creates_single_key(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        self.assertEqual(
            license.license_keys.count(),
            1
        )

    def test_license_string(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        self.assertIn(
            "user@test.com",
            str(license)
        )

    def test_license_key_string_returns_key(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        key = license.license_keys.first()

        self.assertEqual(
            str(key),
            key.key
        )

    def test_license_activity_string_with_key(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        key = license.license_keys.first()

        activity = LicenseActivity.objects.create(
            license_key=key,
            action="activate",
            device_id="abc"
        )

        self.assertIn(
            "activate",
            str(activity)
        )

    def test_package_config_string(self):
        config = PackageConfig.objects.create(
            package="agency",
            max_licenses=2
        )

        self.assertIn(
            "agency",
            str(config)
        )

    def test_generated_keys_are_unique(self):
        license1 = create_license(
            self.user,
            "player",
            self.order
        )

        order2 = Order.objects.create(
            user=self.user,
            package="player",
            amount=4900,
            status="paid"
        )

        license2 = create_license(
            self.user,
            "player",
            order2
        )

        key1 = license1.license_keys.first().key
        key2 = license2.license_keys.first().key

        self.assertNotEqual(key1, key2)

    def test_license_key_defaults_active(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        key = license.license_keys.first()

        self.assertTrue(key.is_active)

    def test_license_defaults_active(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        self.assertTrue(license.is_active)

    def test_license_activity_string_with_direct_license(self):
        license = create_license(
            self.user,
            "player",
            self.order
        )

        activity = LicenseActivity.objects.create(
            license=license,
            action="validate",
            device_id="abc"
        )

        self.assertIn(
            "validate",
            str(activity)
        )

        self.assertIn(
            "user@test.com",
            str(activity)
        )


    def test_license_activity_string_without_license_or_key(self):
        activity = LicenseActivity.objects.create(
            action="failed",
            device_id="abc"
        )

        self.assertEqual(
            str(activity),
            "Unknown License | failed"
        )


    def test_generate_activation_key_prefix(self):
        key = generate_activation_key()

        self.assertTrue(
            key.startswith("SD-")
        )