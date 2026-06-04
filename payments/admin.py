from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "package",
        "amount_display",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "package",
        "created_at",
    )

    search_fields = (
        "user__email",
        "stripe_session_id",
    )

    readonly_fields = (
        "stripe_session_id",
        "created_at",
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    list_per_page = 25

    @admin.display(description="Amount")
    def amount_display(self, obj):
        return f"€{obj.amount / 100:.2f}"