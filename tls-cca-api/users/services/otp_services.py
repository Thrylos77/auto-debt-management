from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from users.models import User, OTP
from users.utils import generate_otp, send_otp_email
from django.contrib.auth.password_validation import validate_password

COOLDOWN_SECONDS = 120

def can_request_new_otp(user: User):
    """Check if the user can request a new OTP based on a cooldown period."""
    last_otp = OTP.objects.filter(user=user).order_by('-created_at').first()
    if not last_otp:
        return True, 0

    next_allowed_time = last_otp.created_at + timedelta(seconds=COOLDOWN_SECONDS)
    if timezone.now() < next_allowed_time:
        remaining = int((next_allowed_time - timezone.now()).total_seconds())
        return False, remaining
    return True, 0

def request_password_reset_otp(user: User):
    """Generate, save, and send a new password reset OTP for a user."""
    can_request, remaining = can_request_new_otp(user)
    if not can_request:
        raise ValidationError(
            {"detail": f"Please wait {remaining} seconds before requesting a new OTP."}
        )
    
    code = generate_otp()
    OTP.objects.create(user=user, code=code)
    send_otp_email(user.email, code)

def reset_password_with_otp(user: User, otp_code: str, new_password: str):
    """Validate the OTP and reset the user's password."""
    otp_qs = OTP.objects.filter(user=user, code=otp_code, is_used=False)
    if not otp_qs.exists():
        raise ValidationError({"otp": "Invalid or used OTP."})
    
    otp_obj = otp_qs.latest('created_at')
    if not otp_obj.is_valid():
        raise ValidationError({"otp": "OTP expired."})

    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save()
    otp_obj.is_used = True
    otp_obj.save()