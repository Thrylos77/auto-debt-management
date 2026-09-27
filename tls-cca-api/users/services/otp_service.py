from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from users.models import OTP
from users.utils import generate_otp

COOLDOWN_SECONDS = 120


def can_request_new_otp(user):
    last_otp = OTP.objects.filter(user=user).order_by("-created_at").first()
    if not last_otp:
        return True, 0
    next_allowed = last_otp.created_at + timedelta(seconds=COOLDOWN_SECONDS)
    remaining = int(max(0, (next_allowed - timezone.now()).total_seconds()))
    return (remaining == 0), remaining


@transaction.atomic
def request_password_reset_otp(user):
    can_request, remaining = can_request_new_otp(user)
    if not can_request:
        raise ValidationError({"detail": f"Please wait {remaining} seconds before requesting a new OTP."})

    raw_code = generate_otp()
    otp = OTP.objects.create(
        user=user,
        code_hash=make_password(raw_code),
        expires_at=timezone.now() + timedelta(minutes=OTP.EXPIRATION_MINUTES),
    )

    try:
        from .email_gateway import send_password_reset_otp
        send_password_reset_otp(email=user.email, otp=raw_code)
    except Exception as exc:
        otp.delete()
        raise ValidationError({"detail": "Unable to send OTP."}) from exc
    return otp


@transaction.atomic
def reset_password_with_otp(user, otp_code, new_password):
    otp = (
        OTP.objects.select_for_update()
        .filter(user=user, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise ValidationError({"otp": "Invalid OTP."})
    if not otp.is_valid():
        raise ValidationError({"otp": "OTP expired or invalid."})
    if not otp.check_code(otp_code):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise ValidationError({"otp": "Invalid OTP."})

    otp.is_used = True
    otp.used_at = timezone.now()
    otp.save(update_fields=["is_used", "used_at"])

    from .password_service import PasswordService
    PasswordService().change_password(user, new_password, actor=user, force=True)
    return user
