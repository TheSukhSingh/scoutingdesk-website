import uuid
from django.db import models
from django.contrib.auth import get_user_model

from payments.models import Order

User = get_user_model()



def generate_activation_key():
    while True:
        key = f"SD-{uuid.uuid4().hex[:12].upper()}"
        if not License.objects.filter(key=key).exists():
            return key


class License(models.Model):
    PACKAGE_CHOICES = [
        ('player', 'Player'),
        ('agency', 'Agency'),
        ('club', 'Club'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="licenses")

    key = models.CharField(max_length=32, unique=True, default=generate_activation_key)

    package = models.CharField(max_length=20, choices=PACKAGE_CHOICES)

    is_active = models.BooleanField(default=True)

    # 🔐 Device binding (Phase 2 use)
    device_id = models.CharField(max_length=255, null=True, blank=True)

    # 📊 Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    session_token = models.CharField(max_length=255, null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    # 💰 Link to order
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.package} - {self.key}"
    

class LicenseActivity(models.Model):
    ACTION_CHOICES = [
        ('activate', 'Activate'),
        ('validate', 'Validate'),
        ('failed', 'Failed Attempt'),
        ('switch', 'Device Switch'),
    ]

    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    device_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.license.key} - {self.action}"



