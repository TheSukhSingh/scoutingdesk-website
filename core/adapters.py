from allauth.account.adapter import DefaultAccountAdapter

from activation.utils import get_client_ip
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

    def get_client_ip(self, request):
        return get_client_ip(request)
    def send_mail(self, *args, **kwargs):
        print("🔥 SEND_MAIL")
        return super().send_mail(*args, **kwargs)

    def render_mail(self, *args, **kwargs):
        print("🔥 RENDER_MAIL")
        return super().render_mail(*args, **kwargs)
    # def send_mail(self, template_prefix, email, context):

    #     if template_prefix == "account/email/email_confirmation":

    #         send_verification_email(
    #             user=context["user"],
    #             activate_url=context["activate_url"],
    #         )

    #     elif template_prefix == "account/email/password_reset_key":

    #         send_password_reset_email(
    #             user=context["user"],
    #             reset_url=(
    #                 context.get("password_reset_url")
    #                 or context.get("reset_url")
    #             ),
    #         )

    #     else:
    #         super().send_mail(template_prefix, email, context)