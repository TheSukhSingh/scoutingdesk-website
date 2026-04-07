from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages

def custom_login(request):
    if request.method == "POST":
        email = request.POST.get("login")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user:
            profile = user.profile

            if profile.is_locked:
                messages.error(request, "Account locked due to multiple failed attempts.")
                return redirect("account_login")

            # reset attempts
            profile.failed_attempts = 0
            profile.save()

            login(request, user)
            return redirect("/")

        else:
            # handle failed attempt
            from django.contrib.auth import get_user_model
            User = get_user_model()

            try:
                user = User.objects.get(email=email)
                profile = user.profile

                profile.failed_attempts += 1

                if profile.failed_attempts >= 5:
                    profile.is_locked = True

                profile.save()

            except User.DoesNotExist:
                pass

            messages.error(request, "Invalid credentials")

    return render(request, "account/login.html")