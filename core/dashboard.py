from datetime import timedelta

from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from activation.models import License
from payments.models import Order

User = get_user_model()


def dashboard_callback(request, context):

    now = timezone.now()

    last_7_days = now - timedelta(days=7)

    last_30_days = now - timedelta(days=30)

    # =========================
    # COUNTS
    # =========================

    total_users = User.objects.count()

    active_licenses = License.objects.filter(
        is_active=True
    ).count()

    total_orders = Order.objects.count()

    successful_orders = Order.objects.filter(
        status="paid"
    ).count()

    # =========================
    # REVENUE
    # =========================

    total_revenue = (
        Order.objects.filter(
            status="paid"
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0
    ) / 100

    weekly_revenue = (
        Order.objects.filter(
            status="paid",
            created_at__gte=last_7_days
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0
    ) / 100

    monthly_revenue = (
        Order.objects.filter(
            status="paid",
            created_at__gte=last_30_days
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0
    ) / 100

    # =========================
    # RECENT PAYMENTS
    # =========================

    recent_payments = (
        Order.objects
        .filter(status="paid")
        .select_related("user")
        .order_by("-created_at")[:5]
    )

    # =========================
    # REVENUE GRAPH DATA
    # =========================

    revenue_labels = []
    revenue_data = []

    for i in range(6, -1, -1):

        day = now - timedelta(days=i)

        start_day = day.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end_day = day.replace(
            hour=23,
            minute=59,
            second=59
        )

        revenue = (
            Order.objects.filter(
                status="paid",
                created_at__range=(start_day, end_day)
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0
        ) / 100

        revenue_labels.append(day.strftime("%a"))

        revenue_data.append(float(revenue))

    # =========================
    # LICENSE GRAPH DATA
    # =========================

    license_labels = []
    license_data = []

    for i in range(6, -1, -1):

        day = now - timedelta(days=i)

        start_day = day.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end_day = day.replace(
            hour=23,
            minute=59,
            second=59
        )

        count = License.objects.filter(
            created_at__range=(start_day, end_day)
        ).count()

        license_labels.append(day.strftime("%a"))

        license_data.append(count)

    context.update({

        # =====================
        # STATS
        # =====================

        "dashboard_stats": {

            "total_users": total_users,

            "active_licenses": active_licenses,

            "total_orders": total_orders,

            "successful_orders": successful_orders,

            "total_revenue": total_revenue,

            "weekly_revenue": weekly_revenue,

            "monthly_revenue": monthly_revenue,

        },

        # =====================
        # CHARTS
        # =====================

        "revenue_chart": {
            "labels": revenue_labels,
            "data": revenue_data,
        },

        "license_chart": {
            "labels": license_labels,
            "data": license_data,
        },

        # =====================
        # RECENT PAYMENTS
        # =====================

        "recent_payments": recent_payments,
        "new_users_week": User.objects.filter(
            date_joined__gte=last_7_days
        ).count(),

        "licenses_this_week": License.objects.filter(
            created_at__gte=last_7_days
        ).count(),

        "payments_this_week": Order.objects.filter(
            status="paid",
            created_at__gte=last_7_days
        ).count(),
    })

    return context