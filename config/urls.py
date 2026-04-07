from django.contrib import admin
from django.urls import include, path
from core.views import home

from core.auth_views import custom_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', custom_login, name='account_login'),
    path('accounts/', include('allauth.urls')),
    path('', home),
    path('payments/', include('payments.urls')),
]