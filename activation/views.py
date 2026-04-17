from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

import json
import hashlib
import hmac
import time
import uuid

from .models import License, LicenseActivity
from .utils import get_client_ip


# 🔐 Hash device
def hash_device(device_id):
    return hashlib.sha256(device_id.encode()).hexdigest()


# 🔐 Verify request signature
def verify_signature(key, device_id, timestamp, signature):
    message = f"{key}{device_id}{timestamp}".encode()
    secret = settings.CLIENT_SECRET.encode()
    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# 🔑 ACTIVATE LICENSE
@csrf_exempt
def activate_license(request):
    if request.method != "POST":
        return JsonResponse({"valid": False, "error": "Invalid request method"})

    try:
        data = json.loads(request.body)

        key = data.get("activation_key")
        device_id = data.get("device_id")
        timestamp = data.get("timestamp")
        signature = data.get("signature")

        if not key or not device_id or not timestamp or not signature:
            return JsonResponse({"valid": False, "error": "Missing data"})

        # ⏳ Prevent replay attack
        if abs(time.time() - int(timestamp)) > 300:
            return JsonResponse({"valid": False, "error": "Request expired"})

        # 🔐 Verify signature
        if not verify_signature(key, device_id, timestamp, signature):
            return JsonResponse({"valid": False, "error": "Invalid signature"})

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

        # 🚨 Device switch limit
        recent_switches = LicenseActivity.objects.filter(
            license=license,
            action='switch',
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()

        if recent_switches >= 5:
            return JsonResponse({"valid": False, "error": "Too many device switches"})

        # 🔑 Generate session token
        token = str(uuid.uuid4())
        license.session_token = token
        license.token_expires_at = timezone.now() + timezone.timedelta(days=7)

        # 🟢 First activation
        if not license.device_id:
            license.device_id = hashed_device
            license.activated_at = timezone.now()

        # 🔄 Soft lock (replace device)
        elif license.device_id != hashed_device:
            LicenseActivity.objects.create(
                license=license,
                action='switch',
                device_id=hashed_device,
                ip_address=ip
            )
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


# 🔁 RESET DEVICE
@csrf_exempt
def reset_device(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        license = License.objects.get(key=key)

        license.device_id = None
        license.session_token = None
        license.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

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
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        license = License.objects.get(key=key)

        license.device_id = None
        license.session_token = None
        license.save()

        return JsonResponse({"success": True})

    except License.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not allowed"})
    
import uuid

def generate_unique_key():
    while True:
        key = f"SD-{uuid.uuid4().hex[:12].upper()}"
        if not License.objects.filter(key=key).exists():
            return key
        
@login_required
def regenerate_key(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body)
        key = data.get("activation_key")

        license = License.objects.get(key=key)

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

    except License.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not allowed"})