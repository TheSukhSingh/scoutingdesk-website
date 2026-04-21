from django.urls import path
from .views import (
    activate_license,
    validate_license,
    get_user_licenses,
    dashboard_reset_device,
    regenerate_key
)

urlpatterns = [
    path('activate/', activate_license),
    path('validate/', validate_license),

    # 🧠 dashboard APIs
    path('my-licenses/', get_user_licenses),
    path('reset-device/', dashboard_reset_device),
    path('regenerate-key/', regenerate_key),
]