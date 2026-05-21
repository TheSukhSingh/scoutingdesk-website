from django.contrib import admin
from .models import UserProfile, AuthActivity


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "plan",
        "is_locked",
        "failed_attempts",
        "created_at",
    )

    list_filter = (
        "plan",
        "is_locked",
    )

    search_fields = (
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "plan_updated_at",
        "last_failed_at",
        "locked_until",
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    list_per_page = 25


@admin.register(AuthActivity)
class AuthActivityAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "email",
        "action",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "email",
        "ip_address",
    )

    readonly_fields = (
        "user",
        "email",
        "action",
        "ip_address",
        "user_agent",
        "created_at",
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    list_per_page = 50