from django.contrib import admin
from .models import License, LicenseActivity, LicenseKey, PackageConfig


class LicenseActivityInline(admin.TabularInline):
    model = LicenseActivity

    extra = 0

    can_delete = False
    fields = (
        "license_key",
        "action",
        "device_id",
        "ip_address",
        "created_at",
    )
    readonly_fields = (
        "license_key",
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
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__email",
    )

    list_filter = (
        "package",
        "is_active",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
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
            )
        }),

        ("Tracking", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    actions = [
        "activate_selected",
        "deactivate_selected",
    ]

    @admin.action(description="Activate selected licenses")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected licenses")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(LicenseActivity)
class LicenseActivityAdmin(admin.ModelAdmin):

    list_display = (
        "owner_email",
        "license_key_label",
        "package",
        "action",
        "ip_address",
        "created_at",
    )
    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "license__user__email",
        "license_key__key",
        "ip_address",
    )
    readonly_fields = (
        "license",
        "license_key",
        "action",
        "device_id",
        "ip_address",
        "created_at",
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    list_per_page = 50

    list_select_related = (
        "license",
        "license__user",
        "license_key",
        "license_key__license",
        "license_key__license__user",
    )

    def _license(self, obj):
        return obj.license or (
            obj.license_key.license
            if obj.license_key_id and obj.license_key.license_id
            else None
        )

    def owner_email(self, obj):
        license = self._license(obj)

        if license and license.user_id:
            return license.user.email or license.user.username or f"User #{license.user_id}"

        return "Unknown User"

    owner_email.short_description = "Owner"
    owner_email.admin_order_field = "license__user__email"

    def license_key_label(self, obj):
        if obj.license_key_id:
            return obj.license_key.display_name or obj.license_key.key

        return "-"

    license_key_label.short_description = "License Key"
    license_key_label.admin_order_field = "license_key__key"

    def package(self, obj):
        license = self._license(obj)

        if license:
            return license.get_package_display()

        return "-"

    package.short_description = "Package"
    package.admin_order_field = "license__package"

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
        "owner_email",
        "package",
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

    list_select_related = (
        "license",
        "license__user",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50

    def owner_email(self, obj):
        user = obj.license.user

        if user.email:
            return user.email

        if user.username:
            return user.username

        return f"User #{user.id}"

    owner_email.short_description = "Owner"
    
    def package(self, obj):
        return obj.license.get_package_display()

    package.short_description = "Package"