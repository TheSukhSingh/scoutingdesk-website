import stripe
import logging

from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail

from .models import Order
from activation.utils import create_license, deactivate_license_by_order_object
from activation.models import License

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

@login_required
def create_checkout_session(request, package_type):
    package = settings.STRIPE_PRICES.get(package_type)

    if not package:
        return HttpResponse("Invalid package")

    order = Order.objects.create(
        user=request.user,
        package=package_type,
        amount=package["price"],
        status='pending'
    )

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': package["price_id"],
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payments/success/?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=request.build_absolute_uri('/payments/cancel/'),
        metadata={
            'order': order.id
        }
    )

    order.stripe_session_id = session.id
    order.save()

    return redirect(session.url)


# ✅ PAYMENT SUCCESS PAGE
@login_required
def payment_success(request):
    return render(request, "payments/success.html", {
        "plan": request.user.profile.plan
    })


# ❌ PAYMENT CANCEL
@login_required
def payment_cancel(request):
    return HttpResponse("Payment cancelled.")


# 🔌 STRIPE WEBHOOK
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

    # 🟢 PAYMENT SUCCESS
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session["metadata"] if "metadata" in session else {}
        order_id = metadata.get("order")

        if not order_id:
            logger.error("No order in metadata")
            return HttpResponse(status=200)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found: {order_id}")
            return HttpResponse(status=200)

        if order.status != 'paid':
            order.status = 'paid'
            order.save()

            user = order.user
            profile = user.profile

            # 🔥 Assign plan
            profile.plan_updated_at = timezone.now()
            profile.plan = order.package
            profile.failed_attempts = 0
            profile.is_locked = False
            profile.save()

            # 🔑 Prevent duplicate license
            existing_license = License.objects.filter(order=order).first()

            if not existing_license:
                license = create_license(
                    user=user,
                    package=order.package,
                    order=order
                )

                # 📩 Send email
                send_mail(
                    subject="Your ScoutingDesk Plan is Activated 🎉",
                    message=f"""Hi {user.email},

Your payment was successful.

Plan Activated: {order.package.upper()}

🔑 Your Activation Key:
{license.key}

Keep this key safe. You will need it to activate your software.

Thanks,
ScoutingDesk Team
""",
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True,
                )

                logger.info(f"License created for order {order.id}")

            else:
                logger.warning(f"License already exists for order {order.id}")

    # REFUND / CANCEL (SAFE HANDLING FOR NOW)
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']

        payment_intent = charge.get("payment_intent")

        if payment_intent:
            try:
                # 🔍 Find checkout session from payment_intent
                sessions = stripe.checkout.Session.list(
                    payment_intent=payment_intent,
                    limit=1
                )

                if sessions.data:
                    session = sessions.data[0]
                    order_id = session.metadata.get("order")

                    if order_id:
                        try:
                            order = Order.objects.get(id=order_id)
                            deactivate_license_by_order_object(order)
                        except Order.DoesNotExist:
                            logger.error(f"Order not found during refund: {order_id}")

            except Exception as e:
                logger.error(f"Refund handling error: {str(e)}")
    return HttpResponse(status=200)