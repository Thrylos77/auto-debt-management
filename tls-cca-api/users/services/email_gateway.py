"""Temporary email gateway boundary.

Lot 3/5 will replace this adapter with the notifications platform without changing
OTP/password services.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_password_reset_otp(*, email: str, otp: str) -> None:
    subject = "Your One-Time Password (OTP) for Password Reset"
    html_message = render_to_string("emails/otp_email.html", {"otp": otp})
    send_mail(
        subject,
        strip_tags(html_message),
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )
