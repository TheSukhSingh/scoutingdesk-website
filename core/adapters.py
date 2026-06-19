from allauth.account.adapter import DefaultAccountAdapter

from core.emails import (
    send_verification_email,
    send_password_reset_email,
)


class CustomAccountAdapter(DefaultAccountAdapter):

    def populate_username(self, request, user):
        user.username = user.email

    def send_mail(self, template_prefix, email, context):

        if template_prefix == "account/email/email_confirmation":

            send_verification_email(
                user=context["user"],
                activate_url=context["activate_url"],
            )

        elif template_prefix == "account/email/password_reset_key":

            send_password_reset_email(
                user=context["user"],
                reset_url=(
                    context.get("password_reset_url")
                    or context.get("reset_url")
                ),
            )

        else:
            super().send_mail(template_prefix, email, context)