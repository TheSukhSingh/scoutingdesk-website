from django.shortcuts import render

def dev_password_reset(request): #done
    return render(request, "account/password_reset.html")

def dev_password_reset_done(request):
    return render(request, "account/password_reset_done.html")

def dev_password_reset_confirm(request):
    return render(request, "account/password_reset_from_key.html", {
        "form": None  # temporary
    })

def dev_password_reset_complete(request):
    return render(request, "account/password_reset_from_key_done.html")