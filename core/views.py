from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.http import HttpResponse

def home(request):
    return render(request, 'core/home.html')

def home_v2(request):
    return render(request, 'v2/core/home.html')

# def feature_page(request):
#     return render(request, 'core/features.html')

def terms(request):
    return render(request, 'docs/terms.html')

def cookie(request):
    return render(request, 'docs/cookie.html')

def privacy(request):
    return render(request, 'docs/privacy.html')

def terms_v2(request):
    return render(request, 'v2/docs/terms.html')

def cookie_v2(request):
    return render(request, 'v2/docs/cookie.html')

def privacy_v2(request):
    return render(request, 'v2/docs/privacy.html')

@login_required
def dashboard(request):
    return render(request, "dashboard.html")

@login_required
def dashboard_v2(request):
    return render(request, "v2/core/dashboard.html")

def download_page(request):
    return render(request, "download.html")

def download_page_v2(request):
    return render(request, "v2/core/download.html")


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from activation.models import License

@login_required
def get_profile_data(request):

    profile = request.user.profile

    latest_license = License.objects.filter(
        user=request.user
    ).first()

    data = {
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "email": request.user.email,

        "club": profile.club,
        "role": profile.role,

        "plan": profile.plan,

        "created_at": profile.created_at,

        "device_active": bool(
            latest_license.device_id
        ) if latest_license else False,

        "last_seen": (
            latest_license.last_seen
        ) if latest_license else None,
    }

    return JsonResponse(data)

import json

@login_required
def update_profile_data(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request"
        })

    try:
        data = json.loads(request.body)

        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        profile = request.user.profile

        profile.club = data.get("club", "").strip()
        profile.role = data.get("role", "").strip()

        profile.save()

        return JsonResponse({
            "success": True
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        })
    
from django.http import FileResponse
import os

def download_app(request):
    file_path = "/var/www/scoutingdesk/ScoutingDesk_Setup.exe"
    
    if os.path.exists(file_path):
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename="ScoutingDesk_Setup.exe"
        )
    
    return HttpResponse("File not found", status=404)