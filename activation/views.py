import hashlib
import json
import uuid

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from activation.utils import get_client_ip
from .models import LicenseActivity, LicenseKey, PackageConfig


MAX_ACTIVATION_FAILED_ATTEMPTS = 10
MAX_VALIDATE_ATTEMPTS = 30
VALIDATE_WINDOW_MINUTES = 5
PER_PAGE = 20


def hash_device(device_id):
    return hashlib.sha256(device_id.encode()).hexdigest()


def _package_config(license_key):
    return PackageConfig.objects.filter(
        package=license_key.license.package,
        is_active=True,
    ).first()


def _device_reset_cooldown_days(license_key):
    package_config = _package_config(license_key)

    if package_config:
        return package_config.device_reset_cooldown_days

    return 7


def _key_regeneration_cooldown_days(license_key):
    package_config = _package_config(license_key)

    if package_config:
        return package_config.key_regeneration_cooldown_days

    return 30


def _get_owned_license_key(request, key):
    try:
        return (
            LicenseKey.objects
            .select_related("license", "license__user")
            .get(key=key)
        )
    except LicenseKey.DoesNotExist:
        return None


@csrf_exempt
def activate_license(request):
    if request.method != "POST":
        return JsonResponse({"valid": False, "error": "Invalid request method"})

    try:
        data = json.loads(request.body)

        key = data.get("activation_key")
        device_id = data.get("device_id")

        if not key or not device_id:
            return JsonResponse({"valid": False, "error": "Missing data"})

        hashed_device = hash_device(device_id)
        ip = get_client_ip(request)

        failed_attempts = LicenseActivity.objects.filter(
            action='failed',
            ip_address=ip,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).count()

        if failed_attempts >= MAX_ACTIVATION_FAILED_ATTEMPTS:
            return JsonResponse({"valid": False, "error": "Too many attempts"})

        license_key = _get_owned_license_key(request, key)

        if not license_key:
            LicenseActivity.objects.create(
                license=None,
                action='failed',
                device_id=hashed_device,
                ip_address=ip
            )
            return JsonResponse({"valid": False, "error": "Invalid key"})

        license = license_key.license

        if not license.is_active or not license_key.is_active:
            return JsonResponse({"valid": False, "error": "License inactive"})

        if license_key.device_id and license_key.device_id != hashed_device:
            return JsonResponse({
                "valid": False,
                "error": "License already used on another device"
            })

        token = str(uuid.uuid4())
        now = timezone.now()

        license_key.session_token = token
        license_key.token_expires_at = now + timezone.timedelta(days=7)

        if not license_key.device_id:
            license_key.device_id = hashed_device
            license_key.activated_at = now

        license_key.last_seen = now
        license_key.save(update_fields=[
            "device_id",
            "session_token",
            "token_expires_at",
            "activated_at",
            "last_seen",
            "updated_at",
        ])

        LicenseActivity.objects.create(
            license=license,
            action='activate',
            device_id=hashed_device,
            ip_address=ip
        )

        return JsonResponse({
            "valid": True,
            "token": token,
            "package": license.package
        })

    except Exception as e:
        return JsonResponse({"valid": False, "error": str(e)})


@csrf_exempt
def validate_license(request):
    if request.method != "POST":
        return JsonResponse({"valid": False})

    try:
        data = json.loads(request.body)

        token = data.get("token")
        device_id = data.get("device_id")

        if not token or not device_id:
            return JsonResponse({"valid": False})

        hashed_device = hash_device(device_id)
        ip = get_client_ip(request)

        recent_attempts = LicenseActivity.objects.filter(
            action='validate',
            ip_address=ip,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=VALIDATE_WINDOW_MINUTES)
        ).count()

        if recent_attempts >= MAX_VALIDATE_ATTEMPTS:
            return JsonResponse({
                "valid": False,
                "error": "Too many requests. Try again later."
            })

        try:
            license_key = (
                LicenseKey.objects
                .select_related("license")
                .get(session_token=token)
            )
        except LicenseKey.DoesNotExist:
            return JsonResponse({"valid": False, "error": "Invalid session"})

        license = license_key.license

        if not license.is_active or not license_key.is_active:
            return JsonResponse({"valid": False, "error": "License inactive"})

        if not license_key.token_expires_at or license_key.token_expires_at < timezone.now():
            return JsonResponse({"valid": False, "error": "Session expired"})

        if license_key.device_id != hashed_device:
            return JsonResponse({"valid": False, "error": "Device mismatch"})

        token_attempts = LicenseActivity.objects.filter(
            action='validate',
            license=license,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=VALIDATE_WINDOW_MINUTES)
        ).count()

        if token_attempts >= MAX_VALIDATE_ATTEMPTS:
            return JsonResponse({
                "valid": False,
                "error": "Too many validation attempts for this license."
            })

        license_key.last_seen = timezone.now()
        license_key.save(update_fields=["last_seen", "updated_at"])

        LicenseActivity.objects.create(
            license=license,
            action='validate',
            device_id=hashed_device,
            ip_address=ip
        )

        return JsonResponse({
            "valid": True,
            "package": license.package
        })

    except Exception as e:
        return JsonResponse({"valid": False, "error": str(e)})


@login_required
def get_user_licenses(request):
    page = request.GET.get("page", 1)

    license_keys_queryset = (
        LicenseKey.objects
        .select_related("license")
        .filter(license__user=request.user)
        .order_by("-license__created_at", "id")
    )

    paginator = Paginator(
        license_keys_queryset,
        PER_PAGE
    )

    current_page = paginator.get_page(page)

    data = []

    for license_key in current_page.object_list:
        license = license_key.license

        data.append({
            "key": license_key.key,
            "display_name": license_key.display_name,
            "note": license_key.note,
            "package": license.package,
            "license_id": license.id,
            "is_active": license.is_active and license_key.is_active,
            "device_bound": bool(license_key.device_id),
            "created_at": license_key.created_at,
            "activated_at": license_key.activated_at,
            "last_seen": license_key.last_seen,
            "can_regenerate": True,
        })

    return JsonResponse({
        "licenses": data,
        "pagination": {
            "current_page": current_page.number,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "has_next": current_page.has_next(),
            "has_previous": current_page.has_previous(),
            "per_page": PER_PAGE,
        }
    })


@login_required
def dashboard_reset_device(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request"
        })

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        if not key:
            return JsonResponse({
                "success": False,
                "error": "Missing key"
            })

        license_key = _get_owned_license_key(request, key)

        if not license_key:
            return JsonResponse({
                "success": False,
                "error": "License not found"
            })

        license = license_key.license

        if license.user != request.user:
            return JsonResponse({
                "success": False,
                "error": "Not allowed"
            })

        cooldown_days = _device_reset_cooldown_days(license_key)

        if license_key.last_device_reset_at:
            cooldown_end = (
                license_key.last_device_reset_at + timezone.timedelta(days=cooldown_days)
            )
            if timezone.now() < cooldown_end:
                remaining_seconds = (cooldown_end - timezone.now()).total_seconds()
                remaining_days = int(remaining_seconds // 86400) + 1

                return JsonResponse({
                    "success": False,
                    "error": (
                        f"You can reset device after {remaining_days} days"
                    )
                })

        license_key.device_id = None
        license_key.session_token = None
        license_key.token_expires_at = None
        license_key.last_device_reset_at = timezone.now()
        license_key.device_reset_count += 1
        license_key.save(update_fields=[
            "device_id",
            "session_token",
            "token_expires_at",
            "last_device_reset_at",
            "device_reset_count",
            "updated_at",
        ])

        LicenseActivity.objects.create(
            license=license,
            action='reset_device',
            device_id="reset",
            ip_address=get_client_ip(request)
        )

        return JsonResponse({"success": True})

    except Exception:
        return JsonResponse({
            "success": False,
            "error": "Something went wrong"
            })


def generate_unique_key():
    while True:
        key = f"SD-{uuid.uuid4().hex[:12].upper()}"
        if not LicenseKey.objects.filter(key=key).exists():
            return key


@login_required
def regenerate_key(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request"
        })

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        if not key:
            return JsonResponse({
                "success": False,
                "error": "Missing key"
                })

        license_key = _get_owned_license_key(request, key)

        if not license_key:
            return JsonResponse({
                "success": False,
                "error": "License not found"
                })

        license = license_key.license

        if license.user != request.user:
            return JsonResponse({
                "success": False,
                "error": "Not allowed"
                })

        cooldown_days = _key_regeneration_cooldown_days(license_key)

        if license_key.last_key_regenerated_at:
            cooldown_end = license_key.last_key_regenerated_at + timezone.timedelta(days=cooldown_days)

            if timezone.now() < cooldown_end:
                remaining_seconds = (cooldown_end - timezone.now()).total_seconds()
                remaining_days = int(remaining_seconds // 86400) + 1
                return JsonResponse({
                    "success": False,
                    "error": f"You can regenerate key after {remaining_days} days"
                })

        new_key = generate_unique_key()

        license_key.key = new_key
        license_key.device_id = None
        license_key.session_token = None
        license_key.token_expires_at = None
        license_key.activated_at = None
        license_key.last_seen = None
        license_key.last_key_regenerated_at = timezone.now()
        license_key.key_regeneration_count += 1
        license_key.save(update_fields=[
            "key",
            "device_id",
            "session_token",
            "token_expires_at",
            "activated_at",
            "last_seen",
            "last_key_regenerated_at",
            "key_regeneration_count",
            "updated_at",
        ])

        LicenseActivity.objects.create(
            license=license,
            action='regenerate_key',
            device_id="regenerated",
            ip_address=get_client_ip(request)
        )

        return JsonResponse({
            "success": True,
            "new_key": new_key
        })

    except Exception:
        return JsonResponse({
            "success": False,
            "error": "Something went wrong"
            })
