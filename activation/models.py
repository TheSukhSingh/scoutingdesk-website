import uuid
from django.db import models
from django.contrib.auth import get_user_model
from payments.models import Order

User = get_user_model()

from django.apps import apps

def generate_activation_key():
    LicenseKey = apps.get_model("activation", "LicenseKey")

    while True:
        key = f"SD-{uuid.uuid4().hex[:12].upper()}"

        if not LicenseKey.objects.filter(key=key).exists():
            return key

class License(models.Model):
    PACKAGE_CHOICES = [
        ('player', 'Player'),
        ('agency', 'Agency'),
        ('club', 'Club'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="licenses")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    package = models.CharField(max_length=20, choices=PACKAGE_CHOICES)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta: 
        indexes = [ 
            models.Index(fields=["user"]), 
            models.Index(fields=["created_at"]), 
        ]

    def __str__(self):
        return (
            f"{self.user.email} | "
            f"{self.get_package_display()} "
        )
    

class LicenseActivity(models.Model):
    ACTION_CHOICES = [
        ('activate', 'Activate'),
        ('validate', 'Validate'),
        ('failed', 'Failed Attempt'),
        ('switch', 'Device Switch'),
        ('login_failed', 'Login Failed'),
        ('reset_device', 'Reset Device'), ('regenerate_key', 'Regenerate Key'),
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

    class Meta: 
        verbose_name_plural = "License Activities"
        indexes = [ 
            models.Index(fields=["action"]), 
            models.Index(fields=["created_at"]), 
            models.Index(fields=["ip_address"]), 
        ]

    def __str__(self):
        if self.license:
            return f"License #{self.license.id} - {self.action}"

        return f"No License - {self.action}"
    

class PackageConfig(models.Model):

    PACKAGE_CHOICES = [
        ('player', 'Player'),
        ('agency', 'Agency'),
        ('club', 'Club'),
    ]

    package = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES,
        unique=True
    )

    max_licenses = models.PositiveIntegerField(default=1)

    device_reset_cooldown_days = models.PositiveIntegerField(default=7)

    key_regeneration_cooldown_days = models.PositiveIntegerField(default=30)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Package Configuration"
        verbose_name_plural = "Package Configurations"

    def __str__(self):
        return (
            f"{self.package} "
            f"(licenses={self.max_licenses})"
        )


class LicenseKey(models.Model):

    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name="license_keys"
    )

    key = models.CharField(
        max_length=32,
        unique=True,
        default=generate_activation_key
    )

    display_name = models.CharField(
        max_length=100,
        blank=True
    )

    note = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(default=True)

    device_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    session_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    token_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    last_key_regenerated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    last_device_reset_at = models.DateTimeField(
        null=True,
        blank=True
    )

    device_reset_count = models.PositiveIntegerField(
        default=0
    )

    key_regeneration_count = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["session_token"]),
            models.Index(fields=["device_id"]),
        ]

    def __str__(self):
        return self.key