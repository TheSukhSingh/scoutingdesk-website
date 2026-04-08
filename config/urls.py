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

from core import dev_views as core_views

urlpatterns += [
    path('dev/reset/', core_views.dev_password_reset),
    path('dev/reset/done/', core_views.dev_password_reset_done),
    path('dev/reset/confirm/', core_views.dev_password_reset_confirm),
    path('dev/reset/complete/', core_views.dev_password_reset_complete),
]