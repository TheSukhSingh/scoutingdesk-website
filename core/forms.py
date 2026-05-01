from allauth.account.forms import SignupForm
from django.contrib.auth import get_user_model
from django import forms

User = get_user_model()

class CustomSignupForm(SignupForm):

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Email already registered. Please login instead."
            )

        return email