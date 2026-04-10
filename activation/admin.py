from django.contrib import admin
from .models import License, LicenseActivity


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("user", "package", "key", "is_active", "device_id", "created_at")
    search_fields = ("user__email", "key")
    list_filter = ("package", "is_active")


@admin.register(LicenseActivity)
class LicenseActivityAdmin(admin.ModelAdmin):
    list_display = ("license", "action", "ip_address", "created_at")
    list_filter = ("action",)
    search_fields = ("license__key",)