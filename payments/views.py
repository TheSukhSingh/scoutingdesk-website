import stripe
import logging

from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.core.paginator import Paginator

from .models import Order
from activation.utils import (
    create_license,
    deactivate_license_by_order_object,
    get_package_license_count,
)
from activation.models import License
from django.db.models import Count, Q, Sum
from django.db import transaction

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

# @login_required
def create_checkout_session(request, package_type):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/signup/?next=/payments/checkout/{package_type}/")
    package = settings.STRIPE_PRICES.get(package_type)

    if not package:
        return HttpResponse("Invalid package", status=400)

    if not package.get("price_id"):
        logger.error("Stripe price ID is not configured for package: %s", package_type)
        return HttpResponse("Payment is not configured for this package.", status=503)

    order = Order.objects.create(
        user=request.user,
        package=package_type,
        amount=package["price"],
        status='pending'
    )

    session = stripe.checkout.Session.create(
        # payment_method_types=['card'],
        line_items=[{
            'price': package["price_id"],
            'quantity': 1,
        }],
        mode='payment',
        billing_address_collection='required',

        tax_id_collection={
            'enabled': True,
        },
        customer_creation="always",
        customer_email=request.user.email,
        invoice_creation={
            "enabled": True,
        },
        automatic_tax={
            'enabled': True,
        },
        success_url=request.build_absolute_uri(
            '/payments/success/?session_id={CHECKOUT_SESSION_ID}'
        ),
        cancel_url=request.build_absolute_uri('/payments/cancel/'),
        metadata={
            'order': str(order.id),
            'package': package_type,
        }
    )

    order.stripe_session_id = session.id
    order.save()

    return redirect(session.url)


def _format_activation_keys(license):
    activation_keys = list(
        license.license_keys.order_by("id").values_list("key", flat=True)
    )

    return "\n".join(
        f"{index}. {activation_key}"
        for index, activation_key in enumerate(activation_keys, start=1)
    )


def _send_activation_email(user, order, license):
    activation_key_lines = _format_activation_keys(license)

    send_mail(
        subject="Your ScoutingDesk Plan is Activated 🎉",
        message=f"""Hi {user.email},

Your payment was successful.

Plan Activated: {order.package.upper()}

🔑 Your Activation Keys:
{activation_key_lines}

Keep these keys safe. Each key activates one ScoutingDesk user/device.
Agency purchases include 2 activation keys. Club purchases include 5 activation keys.

Thanks,
ScoutingDesk Team
""",
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def fulfill_paid_order(order):
    """Mark a Stripe order paid and create its license/key set once."""
    with transaction.atomic():
        order = (
            Order.objects
            .select_related("user", "user__profile")
            .select_for_update(of=("self",))
            .get(pk=order.pk)
        )

        user = order.user
        profile = user.profile

        if order.status != 'paid':
            order.status = 'paid'
            order.save(update_fields=["status"])

        profile.plan_updated_at = timezone.now()
        profile.plan = order.package
        profile.failed_attempts = 0
        profile.is_locked = False
        profile.save(update_fields=[
            "plan_updated_at",
            "plan",
            "failed_attempts",
            "is_locked",
        ])

        license_obj = License.objects.filter(order=order).first()

        if license_obj:
            return order, license_obj, False

        license_obj = create_license(
            user=user,
            package=order.package,
            order=order,
        )

    try:
        _send_activation_email(user, order, license_obj)
    except Exception:
        logger.exception(
            f"Failed sending activation email for order {order.id}"
        )
    logger.info(f"License and activation keys created for order {order.id}. Activation email sent to {user.email}")

    return order, license_obj, True


def _session_get(session, key, default=None):
    if isinstance(session, dict):
        return session.get(key, default)

    return getattr(session, key, default)


def _session_metadata(session):
    metadata = _session_get(session, "metadata", {})

    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()

    return metadata or {}


def _order_from_checkout_session(session):
    metadata = _session_metadata(session)
    order_id = metadata.get("order") or metadata.get("order_id")

    if order_id:
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found: {order_id}")

    session_id = _session_get(session, "id")

    if session_id:
        try:
            return Order.objects.get(stripe_session_id=session_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found for session: {session_id}")

    return None


def _checkout_session_is_paid(session):
    return (
        _session_get(session, "payment_status") == "paid"
        or _session_get(session, "status") == "complete"
    )

@login_required
def payment_success(request):
    session_id = request.GET.get("session_id")
    order = None
    license_obj = None

    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            order = _order_from_checkout_session(session)

            if (
                order
                and order.user_id == request.user.id
                and _checkout_session_is_paid(session)
            ):
                order, license_obj, _ = fulfill_paid_order(order)

        except stripe.error.StripeError:
            pass

    # fallback if page is refreshed
    if order is None:
        order = (
            Order.objects
            .filter(user=request.user, status="paid")
            .order_by("-created_at")
            .first()
        )

    if order and license_obj is None:
        license_obj = License.objects.filter(
            user=request.user,
            order=order
        ).first()

    if order == None:
        plan = None
    else:
        plan = f'{order.package} Package'

    license_keys = []
    if license_obj:
        license_keys = (
            license_obj
            .license_keys
            .filter(is_active=True)
            .order_by("id")
        )

    expected_key_count = 0

    if license_obj:
        expected_key_count = license_obj.license_keys.count()

    return render(
        request,
        "payments/success.html",
        {
            "plan": plan,
            "order": order,
            "license_keys": license_keys,
            "expected_key_count": expected_key_count,
        }
    )

@login_required
def payment_cancel(request):
    return HttpResponse("Payment cancelled.")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        return HttpResponse(status=400)

    logger.info(f"Stripe event received: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order = _order_from_checkout_session(session)

        if order and _checkout_session_is_paid(session):
            try:
                fulfill_paid_order(order)
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.exception(e)
                raise

    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']

        payment_intent = charge.get("payment_intent")

        if payment_intent:
            try:
                sessions = stripe.checkout.Session.list(
                    payment_intent=payment_intent,
                    limit=1
                )

                if sessions.data:
                    session = sessions.data[0]
                    order = _order_from_checkout_session(session)

                    if order:
                        deactivate_license_by_order_object(order)

            except Exception as e:
                logger.error(f"Refund handling error: {str(e)}")

    return HttpResponse(status=200)


@login_required
def billing_history(request):

    page = request.GET.get("page", 1)

    orders_queryset = (
        Order.objects
        .filter(user=request.user)
        .order_by("-created_at")
    )



    # SUMMARY
    summary = orders_queryset.aggregate(

        successful_payments=Count(
            "id",
            filter=Q(status="paid")
        ),

        total_spent=Sum(
            "amount",
            filter=Q(status="paid")
        )
    )



    # PAGINATION
    paginator = Paginator(
        orders_queryset,
        10
    )

    orders = paginator.get_page(page)



    data = []

    start_index = (
        (orders.number - 1)
        * paginator.per_page
    )



    for index, order in enumerate(orders, start=1):

        data.append({

            "serial_number":
                start_index + index,

            "package":
                order.package,

            "amount":
                order.amount / 100,

            "status":
                order.status,

            "created_at":
                order.created_at,

            "session_id": (
                order.stripe_session_id[:20] + "..."
                if order.stripe_session_id
                else "-"
            )
        })



    return JsonResponse({

        "summary": {

            "successful_payments":
                summary["successful_payments"] or 0,

            "total_spent":
                (summary["total_spent"] or 0) / 100.0,
        },



        "orders": data,



        "pagination": {

            "current_page":
                orders.number,

            "total_pages":
                paginator.num_pages,

            "has_next":
                orders.has_next(),

            "has_previous":
                orders.has_previous(),
        }
    })