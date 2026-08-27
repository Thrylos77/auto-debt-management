""" users/services/otp_services.py """

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from users.models import User, OTP
from users.utils import generate_otp, send_otp_email

COOLDOWN_SECONDS = 120

def can_request_new_otp(user: User):
    last_otp = OTP.objects.filter(user=user).order_by('-created_at').first()
    if not last_otp:
        return True, 0

    next_allowed_time = last_otp.created_at + timedelta(seconds=COOLDOWN_SECONDS)
    if timezone.now() < next_allowed_time:
        remaining = int((next_allowed_time - timezone.now()).total_seconds())
        return False, remaining

    return True, 0

@transaction.atomic
def request_password_reset_otp(user: User):
    can_request, remaining = can_request_new_otp(user)
    if not can_request:
        raise ValidationError({
            "detail": f"Please wait {remaining} seconds before requesting a new OTP."
        })

    raw_code = generate_otp()

    otp = OTP.objects.create(
        user=user,
        code_hash=make_password(raw_code),
        expires_at=timezone.now() + timedelta(minutes=OTP.EXPIRATION_MINUTES),
    )

    try:
        send_otp_email(user.email, raw_code)
    except Exception:
        otp.delete()
        raise ValidationError({"detail": "Unable to send OTP."})

    return otp

@transaction.atomic
def reset_password_with_otp(user: User, otp_code: str, new_password: str):
    otp_obj = (
        OTP.objects
        .filter(user=user, is_used=False)
        .order_by('-created_at')
        .first()
    )

    if not otp_obj:
        raise ValidationError({"otp": "Invalid OTP."})

    if not otp_obj.is_valid():
        raise ValidationError({"otp": "OTP expired or invalid."})

    if not otp_obj.check_code(otp_code):
        otp_obj.attempts += 1
        otp_obj.save(update_fields=['attempts'])
        raise ValidationError({"otp": "Invalid OTP."})

    validate_password(new_password, user=user)

    user.set_password(new_password)
    user.save(update_fields=['password'])

    otp_obj.is_used = True
    otp_obj.save(update_fields=['is_used'])