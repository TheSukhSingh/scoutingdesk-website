from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<str:package_type>/', views.create_checkout_session, name='checkout'),
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
    path('webhook/', views.stripe_webhook, name='webhook'),
]