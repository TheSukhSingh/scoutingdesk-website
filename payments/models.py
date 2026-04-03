from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Package(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()  # in cents (Stripe uses cents)
    stripe_price_id = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    PACKAGE_CHOICES = [
        ('player', 'Player'),
        ('agency', 'Agency'),
        ('club', 'Club'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package = models.CharField(max_length=20, choices=PACKAGE_CHOICES)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.package} - {self.status}"