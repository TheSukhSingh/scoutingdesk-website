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