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

def download_page(request):
    return render(request, "download.html")

def download_page_v2(request):
    return render(request, "v2/core/download.html")

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