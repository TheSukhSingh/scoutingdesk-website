import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Package, Order
from django.http import HttpResponse
from django.shortcuts import render
stripe.api_key = settings.STRIPE_SECRET_KEY
from django.core.mail import send_mail

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
            'order_id': order.id
        }
    )

    order.stripe_session_id = session.id
    order.save()

    return redirect(session.url)



@login_required
def payment_success(request):
    return render(request, "payments/success.html", {
        "plan": request.user.profile.plan
    })


@login_required
def payment_cancel(request):
    return HttpResponse("Payment cancelled.")



from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata']['order_id']

        order = Order.objects.get(id=order_id)

        if order.status != 'paid':
            order.status = 'paid'
            order.save()

            # 🔥 Assign plan
            user = order.user
            profile = user.profile
            profile.plan_updated_at = timezone.now()
            profile.plan = order.package
            profile.failed_attempts = 0
            profile.is_locked = False
            profile.save()
            
            send_mail(
                subject="Your ScoutingDesk Plan is Activated 🎉",
                message=f"""Hi {user.email},

            Your payment was successful.

            Plan Activated: {order.package.upper()}

            You can now access your dashboard.

            Thanks,
            ScoutingDesk Team
            """,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )

    return HttpResponse(status=200)