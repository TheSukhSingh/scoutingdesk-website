from django.contrib import admin
from django.urls import include, path
from core.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('', home),
    path('payments/', include('payments.urls')),
]
