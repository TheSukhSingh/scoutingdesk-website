from django.contrib import admin
from .models import License, LicenseActivity, LicenseKey, PackageConfig


class LicenseActivityInline(admin.TabularInline):
    model = LicenseActivity

    extra = 0

    can_delete = False

    readonly_fields = (
        "action",
        "device_id",
        "ip_address",
        "created_at",
    )

    ordering = ("-created_at",)


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "package",
        "key",
        "is_active",
        "device_bound",
        "created_at",
        "last_seen",
    )

    search_fields = (
        "user__email",
        "key",
    )

    list_filter = (
        "package",
        "is_active",
        "created_at",
        "activated_at",
    )

    readonly_fields = (
        "key",
        "session_token",
        "created_at",
        "updated_at",
        "activated_at",
        "last_seen",
        "device_reset_count",
        "key_regeneration_count",
        "last_key_regenerated_at",
        "last_device_reset_at",
    )

    ordering = ("-created_at",)

    list_per_page = 25

    date_hierarchy = "created_at"

    inlines = [LicenseActivityInline]

    fieldsets = (

        ("License Info", {
            "fields": (
                "user",
                "order",
                "package",
                "is_active",
                "key",
            )
        }),

        ("Device Security", {
            "fields": (
                "device_id",
                "session_token",
                "token_expires_at",
            )
        }),

        ("Tracking", {
            "fields": (
                "created_at",
                "updated_at",
                "activated_at",
                "last_seen",
            )
        }),

        ("Security Actions", {
            "fields": (
                "device_reset_count",
                "key_regeneration_count",
                "last_device_reset_at",
                "last_key_regenerated_at",
            )
        }),
    )

    actions = [
        "activate_selected",
        "deactivate_selected",
        "reset_device_binding",
    ]

    @admin.display(boolean=True, description="Device")
    def device_bound(self, obj):
        return bool(obj.device_id)

    @admin.action(description="Activate selected licenses")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected licenses")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Reset device binding")
    def reset_device_binding(self, request, queryset):
        queryset.update(
            device_id=None,
            session_token=None,
            token_expires_at=None,
        )


@admin.register(LicenseActivity)
class LicenseActivityAdmin(admin.ModelAdmin):

    list_display = (
        "license",
        "action",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "license__key",
        "ip_address",
    )

    readonly_fields = (
        "license",
        "action",
        "device_id",
        "ip_address",
        "created_at",
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    list_per_page = 50

@admin.register(PackageConfig)
class PackageConfigAdmin(admin.ModelAdmin):

    list_display = (
        "package",
        "max_licenses",
        "device_reset_cooldown_days",
        "key_regeneration_cooldown_days",
        "is_active",
    )

    list_editable = (
        "max_licenses",
        "device_reset_cooldown_days",
        "key_regeneration_cooldown_days",
        "is_active",
    )


@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):

    list_display = (
        "key",
        "license",
        "display_name",
        "is_active",
        "activated_at",
        "last_seen",
    )

    search_fields = (
        "key",
        "display_name",
        "license__user__email",
    )

    list_filter = (
        "is_active",
        "license__package",
    )