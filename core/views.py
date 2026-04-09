from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.http import HttpResponse

def home(request):
    return render(request, 'core/home.html')

def feature_page(request):
    return render(request, 'core/features.html')

def terms(request):
    return render(request, 'docs/terms.html')

def privacy(request):
    return render(request, 'docs/privacy.html')

