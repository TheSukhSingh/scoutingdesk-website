from allauth.account.adapter import DefaultAccountAdapter
from core.emails import (
    send_verification_email,
    send_password_reset_email,
)


class CustomAccountAdapter(DefaultAccountAdapter):

    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        return True

    def get_signup_redirect_url(self, request):
        return "/#packages"

    def render_mail(self, template_prefix, email, context, headers=None):

        print("🔥", template_prefix)

        if template_prefix == "account/email/email_confirmation":

            send_verification_email(
                context["user"],
                context["activate_url"]
            )

            return None

        elif template_prefix == "account/email/password_reset_key":

            send_password_reset_email(
                context["user"],
                context["password_reset_url"]
            )

            return None

        return super().render_mail(
            template_prefix,
            email,
            context,
            headers=headers
        )