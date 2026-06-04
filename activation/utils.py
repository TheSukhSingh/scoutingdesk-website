from .models import License, LicenseKey, PackageConfig


DEFAULT_PACKAGE_LICENSE_COUNTS = {
    "player": 1,
    "agency": 2,
    "club": 5,
}


def get_package_config(package):
    return PackageConfig.objects.filter(
        package=package,
        is_active=True,
    ).first()


def get_package_license_count(package):
    package_config = get_package_config(package)

    if package_config:
        return package_config.max_licenses

    return DEFAULT_PACKAGE_LICENSE_COUNTS.get(package, 1)


def create_license(user, package, order=None):
    license = License.objects.create(
        user=user,
        package=package,
        order=order
    )

    license_count = get_package_license_count(package)

    LicenseKey.objects.bulk_create([
        LicenseKey(
            license=license,
            display_name=(
                f"{license.get_package_display()} Seat {index}"
                if license_count > 1
                else "Primary Seat"
            )
        )
        for index in range(1, license_count + 1)
    ])

    return license

from django.utils import timezone


def deactivate_license_by_order_object(order):
    licenses = License.objects.filter(order=order)

    licenses.update(
        is_active=False,
        updated_at=timezone.now()
    )

    LicenseKey.objects.filter(
        license__order=order
    ).update(
        is_active=False,
        updated_at=timezone.now()
    )


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')
