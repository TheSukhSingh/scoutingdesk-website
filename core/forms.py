from allauth.account.forms import SignupForm
from django.contrib.auth import get_user_model
from django import forms

User = get_user_model()

class CustomSignupForm(SignupForm):

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "This email is already registered. Try logging in or resetting your password."
            )

        return email