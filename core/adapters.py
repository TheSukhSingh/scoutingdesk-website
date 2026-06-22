from allauth.account.adapter import DefaultAccountAdapter

from activation.utils import get_client_ip
from core.emails import (
    send_password_reset_email,
)


class CustomAccountAdapter(DefaultAccountAdapter):

    def populate_username(self, request, user):
        user.username = user.email

    def is_open_for_signup(self, request):
        return True

    def get_signup_redirect_url(self, request):
        return "/#packages"

    def get_client_ip(self, request):
        return get_client_ip(request)
    def send_mail(self, template_prefix, email, context):


        # if "email_confirmation" in template_prefix:

        #     send_verification_email(
        #         user=context["user"],
        #         activate_url=context["activate_url"]
        #     )
        #     return

        if "password_reset" in template_prefix:

            send_password_reset_email(
                user=context["user"],
                reset_url=(
                    context.get("password_reset_url")
                    or context.get("reset_url")
                )
            )
            return

        return super().send_mail(template_prefix, email, context)
