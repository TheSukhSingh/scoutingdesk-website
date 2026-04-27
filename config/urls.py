from django.contrib import admin
from django.urls import include, path
from core.views import *

from core.auth_views import custom_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', custom_login, name='account_login'),
    path('accounts/', include('allauth.urls')),
    path('', home, name="home"),
    # path('inside/', feature_page, name="inside"),
    path('terms/', terms, name="terms"),
    path('cookie/', cookie, name="cookie"),
    path('privacy/', privacy, name="privacy"),
    path('payments/', include('payments.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('download/', download_page, name='download'),
    path('api/license/', include('activation.urls')),
]
from django.http import HttpResponseForbidden

def block_social(request):
    return HttpResponseForbidden("Social login disabled")

urlpatterns += [
    path('accounts/google/login/', block_social),
    path('accounts/google/login/callback/', block_social),
]
