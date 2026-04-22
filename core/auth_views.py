from django.contrib.auth import authenticate, login, get_user_model
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from activation.models import LicenseActivity
User = get_user_model()
MAX_LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_MINUTES = 10

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def custom_login(request):
    if request.method == "POST":
        email = request.POST.get("login")
        password = request.POST.get("password")
        ip = get_client_ip(request)

        recent_attempts = LicenseActivity.objects.filter(
            action='login_failed',
            ip_address=ip,
            created_at__gte=timezone.now() - timedelta(minutes=LOGIN_WINDOW_MINUTES)
        ).count()

        if recent_attempts >= MAX_LOGIN_ATTEMPTS:
            messages.error(request, "Too many login attempts. Try again later.")
            return redirect("account_login")
        try:
            user_obj = User.objects.get(email=email)
            profile = user_obj.profile

            # 🔓 AUTO RESET FAILED ATTEMPTS AFTER COOLDOWN
            if profile.last_failed_at:
                if timezone.now() - profile.last_failed_at > timedelta(minutes=15):
                    profile.failed_attempts = 0
                    profile.is_locked = False
                    profile.locked_until = None
                    profile.save()

            # 🔒 CHECK LOCK BEFORE AUTHENTICATION
            if profile.is_locked:
                if profile.locked_until and timezone.now() > profile.locked_until:
                    profile.is_locked = False
                    profile.failed_attempts = 0
                    profile.locked_until = None
                    profile.save()
                else:
                    remaining = int((profile.locked_until - timezone.now()).total_seconds() // 60) if profile.locked_until else 0
                    messages.error(request, f"Account locked. Try again in {remaining} minutes.")
                    return redirect("account_login")

        except User.DoesNotExist:
            user_obj = None
            profile = None

        # 🔐 NOW authenticate (AFTER checks)
        user = authenticate(request, email=email, password=password)

        if user:
            profile = user.profile

            # ✅ RESET ON SUCCESS
            profile.failed_attempts = 0
            profile.is_locked = False
            profile.locked_until = None
            profile.last_failed_at = None
            profile.save()

            login(request, user)
            return redirect("/")

        else:
            # ❌ HANDLE FAILED ATTEMPT
            if user_obj and profile:
                profile.failed_attempts += 1
                profile.last_failed_at = timezone.now()

                if profile.failed_attempts >= 5:
                    profile.is_locked = True
                    profile.locked_until = timezone.now() + timedelta(minutes=15)

                profile.save()
            LicenseActivity.objects.create(
                license=None,
                action='login_failed',
                device_id="login",
                ip_address=ip
            )
            messages.error(request, "Invalid credentials")

    return render(request, "account/login.html")