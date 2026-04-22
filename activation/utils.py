from .models import License


def create_license(user, package, order=None):
    license = License.objects.create(
        user=user,
        package=package,
        order=order
    )
    return license


def deactivate_license_by_order_object(order):
    try:
        license = License.objects.filter(order=order).first()
        if license:
            license.is_active = False
            license.save()
    except License.DoesNotExist:
        pass


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')