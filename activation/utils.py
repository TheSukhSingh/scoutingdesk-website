from .models import License


def create_license(user, package, order_id=None):
    license = License.objects.create(
        user=user,
        package=package,
        order_id=order_id
    )
    return license


def deactivate_license_by_order(order_id):
    try:
        license = License.objects.get(order_id=order_id)
        license.is_active = False
        license.save()
    except License.DoesNotExist:
        pass


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')