from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_html_email(
    *,
    subject,
    recipient,
    template_name,
    context,
    text_content=""
):
    html_content = render_to_string(
        template_name,
        context
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient]
    )

    msg.attach_alternative(
        html_content,
        "text/html"
    )

    msg.send()

# def send_verification_email(
#     user,
#     activate_url
# ):
#     send_html_email(
#         subject="Verify your email - ScoutingDesk",
#         recipient=user.email,
#         template_name="emails/verify_email.html",
#         context={
#             "user": user,
#             "activate_url": activate_url,
#         },
#         text_content="Please verify your email."
#     )

def send_password_reset_email(
    user,
    reset_url
):
    send_html_email(
        subject="Reset your password - ScoutingDesk",
        recipient=user.email,
        template_name="emails/password_reset.html",
        context={
            "user": user,
            "reset_url": reset_url,
        },
        text_content="Reset your password."
    )

def send_purchase_email(
    user,
    license,
):
    send_html_email(
        subject="Payment successful - ScoutingDesk",
        recipient=user.email,
        template_name="emails/purchase_success.html",
        context={
            "user": user,
            "package_name": license.get_package_display(),
            "keys": license.license_keys.all(),
            "dashboard_url": "https://scoutingdesk.com/dashboard/",
        },
        text_content="Payment successful."
    )

def send_security_email(
    user,
    action,
    key
):
    send_html_email(
        subject="Security notification - ScoutingDesk",
        recipient=user.email,
        template_name="emails/security_notification.html",
        context={
            "action": action,
            "key": key,
        },
        text_content="Security notification."
    )

    