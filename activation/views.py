from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

import json
import hashlib
import uuid 

from .models import License, LicenseActivity
from .utils import get_client_ip


# 🔐 Hash device
def hash_device(device_id):
    return hashlib.sha256(device_id.encode()).hexdigest()


# 🔑 ACTIVATE LICENSE
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

        # 🚨 Failed attempts protection
        failed_attempts = LicenseActivity.objects.filter(
            action='failed',
            ip_address=ip,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).count()

        if failed_attempts >= 10:
            return JsonResponse({"valid": False, "error": "Too many attempts"})

        try:
            license = License.objects.get(key=key)
        except License.DoesNotExist:
            LicenseActivity.objects.create(
                license=None,
                action='failed',
                device_id=hashed_device,
                ip_address=ip
            )
            return JsonResponse({"valid": False, "error": "Invalid key"})

        if not license.is_active:
            return JsonResponse({"valid": False, "error": "License inactive"})
        
        # 🔒 Device locking (TEMP — will improve in next step)
        if license.device_id and license.device_id != hashed_device:
            return JsonResponse({
                "valid": False,
                "error": "License already used on another device"
            })

        # 🔑 Generate session token
        token = str(uuid.uuid4())
        license.session_token = token
        license.token_expires_at = timezone.now() + timezone.timedelta(days=7)

        # 🟢 First activation
        if not license.device_id:
            license.device_id = hashed_device
            license.activated_at = timezone.now()

        license.last_seen = timezone.now()
        license.save()

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

MAX_VALIDATE_ATTEMPTS = 30
VALIDATE_WINDOW_MINUTES = 5

# 🔁 VALIDATE USING TOKEN (NOT KEY)
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
        # RATE LIMIT: IP + TOKEN
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
            license = License.objects.get(session_token=token)
        except License.DoesNotExist:
            return JsonResponse({"valid": False, "error": "Invalid session"})

        if not license.is_active:
            return JsonResponse({"valid": False, "error": "License inactive"})

        if not license.token_expires_at or license.token_expires_at < timezone.now():
            return JsonResponse({"valid": False, "error": "Session expired"})

        if license.device_id != hashed_device:
            return JsonResponse({"valid": False, "error": "Device mismatch"})
        
        #  RATE LIMIT: TOKEN ABUSE
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
        
        license.last_seen = timezone.now()
        license.save()

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


from django.contrib.auth.decorators import login_required

@login_required
def get_user_licenses(request):
    licenses = License.objects.filter(user=request.user)

    data = []

    for l in licenses:
        data.append({
            "key": l.key,
            "package": l.package,
            "is_active": l.is_active,
            "device_bound": bool(l.device_id),
            "created_at": l.created_at
        })

    return JsonResponse({"licenses": data})

@login_required
def dashboard_reset_device(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"})

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        if not key:
            return JsonResponse({"success": False, "error": "Missing key"})
        
        try:
            license = License.objects.get(key=key)
        except License.DoesNotExist:
            return JsonResponse({"success": False, "error": "License not found"})

        if license.user != request.user:
            return JsonResponse({"success": False, "error": "Not allowed"})
        
        license.device_id = None
        license.session_token = None
        license.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    
import uuid

def generate_unique_key():
    while True:
        key = f"SD-{uuid.uuid4().hex[:12].upper()}"
        if not License.objects.filter(key=key).exists():
            return key
        
@login_required
def regenerate_key(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"})

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        if not key:
            return JsonResponse({"success": False, "error": "Missing key"})
        
        try:
            license = License.objects.get(key=key)
        except License.DoesNotExist:
            return JsonResponse({"success": False, "error": "License not found"})

        if license.user != request.user:
            return JsonResponse({"success": False, "error": "Not allowed"})
        
        # 🔥 generate new key
        new_key = generate_unique_key()

        license.key = new_key
        license.device_id = None
        license.session_token = None
        license.save()

        return JsonResponse({
            "success": True,
            "new_key": new_key
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})