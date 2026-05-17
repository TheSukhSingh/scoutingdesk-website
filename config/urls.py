from django.contrib import admin
from django.urls import include, path
from core.views import *

from core.auth_views import custom_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', custom_login, name='account_login'),
    path('accounts/', include('allauth.urls')),
    
    path('', home, name="home"),
    path('v2/', home_v2, name='home_v2'),

    path('terms/', terms, name="terms"),
    path('cookie/', cookie, name="cookie"),
    path('privacy/', privacy, name="privacy"),
    
    path('v2/terms/', terms_v2, name="terms_v2"),
    path('v2/cookie/', cookie_v2, name="cookie_v2"),
    path('v2/privacy/', privacy_v2, name="privacy_v2"),
    
    path('download/', download_page, name='download'),
    path('v2/download/', download_page_v2, name='download_v2'),
    
    path('dashboard/', dashboard, name='dashboard'),
    path('v2/dashboard/', dashboard_v2, name='dashboard_v2'),
    
    path('payments/', include('payments.urls')),
    path('download/app/', download_app, name='download_app'),
    path('api/license/', include('activation.urls')),

    path('api/profile/', get_profile_data),
    path('api/profile/update/', update_profile_data),
]
from django.http import HttpResponseForbidden

def block_social(request):
    return HttpResponseForbidden("Social login disabled")

urlpatterns += [
    path('accounts/google/login/', block_social),
    path('accounts/google/login/callback/', block_social),
]
