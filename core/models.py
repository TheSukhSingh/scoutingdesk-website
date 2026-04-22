from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfile(models.Model):
    PLAN_CHOICES = [
        ('player', 'Player'),
        ('agency', 'Agency'),
        ('club', 'Club'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, null=True, blank=True)
    plan_updated_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan}"
    


class AuthActivity(models.Model):
    ACTION_CHOICES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('password_reset', 'Password Reset'),
        ('account_locked', 'Account Locked'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email or self.user} - {self.action}"