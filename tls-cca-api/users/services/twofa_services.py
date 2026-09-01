"""
users/services/twofa_services.py

Services 2FA / TOTP using pyotp (compatible Google Authenticator).
"""

import base64
import io
import pyotp
import qrcode
from rest_framework.exceptions import ValidationError
from django.conf import settings


def generate_totp_secret() -> str:
    """Generates a new base32 secret for TOTP (used for 2FA)."""
    return pyotp.random_base32()


def get_totp_uri(user, secret: str) -> str:
    """
    Builds the otpauth:// URI for the QR code.
    Format : otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}
    """
    issuer = settings.TOTP_ISSUER
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email or user.username,
        issuer_name=issuer,
    )


def generate_qr_code_base64(uri: str) -> str:
    """Generates a QR code image and returns it in base64 (data URI)."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifies a TOTP code against a secret. Returns True if valid."""
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def enable_2fa(user, secret: str, code: str):
    """
    Verifies the configuration code and enables 2FA for the user.
    Raises a ValidationError if the code is invalid.
    """
    if not verify_totp_code(secret, code):
        raise ValidationError({"code": "Invalid TOTP code. Please try again."})

    user.totp_secret = secret
    user.is_2fa_enabled = True
    user.save(update_fields=['totp_secret', 'is_2fa_enabled'])


def disable_2fa(user, password: str):
    """Disables 2FA for the user after verifying their password."""
    if not user.check_password(password):
        raise ValidationError({"password": "Incorrect password."})

    user.totp_secret = None
    user.is_2fa_enabled = False
    user.save(update_fields=['totp_secret', 'is_2fa_enabled'])