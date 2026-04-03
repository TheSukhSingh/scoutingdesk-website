import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Package, Order

stripe.api_key = settings.STRIPE_SECRET_KEY


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
        success_url='http://127.0.0.1:8000/payments/success/',
        cancel_url='http://127.0.0.1:8000/payments/cancel/',
        metadata={
            'order_id': order.id
        }
    )

    order.stripe_session_id = session.id
    order.save()

    return redirect(session.url)


from django.http import HttpResponse


@login_required
def payment_success(request):
    return HttpResponse("Payment successful! Redirecting to download page...")


@login_required
def payment_cancel(request):
    return HttpResponse("Payment cancelled.")



from django.views.decorators.csrf import csrf_exempt

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
        order.status = 'paid'
        order.save()

        # 🔥 Send email here (we'll add next step)

    return HttpResponse(status=200)