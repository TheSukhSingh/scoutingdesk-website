from django.urls import path
from .views import *

urlpatterns = [
    path('checkout/<str:package_type>/', create_checkout_session, name='checkout'),
    path('success/', payment_success, name='success'),
    path('cancel/', payment_cancel, name='cancel'),
    path('webhook/', stripe_webhook, name='webhook'),
    path('billing-history/', billing_history),
]