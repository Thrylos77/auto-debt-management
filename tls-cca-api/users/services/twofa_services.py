"""
users/services/twofa_services.py

Services 2FA / TOTP utilisant pyotp (compatible Google Authenticator).
"""

import base64
import io
import pyotp
import qrcode
from rest_framework.exceptions import ValidationError
from django.conf import settings


def generate_totp_secret() -> str:
    """Génère une nouvelle clé secrète TOTP."""
    return pyotp.random_base32()


def get_totp_uri(user, secret: str) -> str:
    """
    Construit l'URI otpauth:// pour le QR code.
    Format : otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}
    """
    issuer = settings.TOTP_ISSUER
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email or user.username,
        issuer_name=issuer,
    )


def generate_qr_code_base64(uri: str) -> str:
    """Génère une image QR code et la retourne en base64 (data URI)."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Vérifie un code TOTP par rapport à un secret. Retourne True si valide."""
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def enable_2fa(user, secret: str, code: str):
    """
    Vérifie le code de configuration et active le 2FA pour l'utilisateur.
    Lève une ValidationError si le code est invalide.
    """
    if not verify_totp_code(secret, code):
        raise ValidationError({"code": "Code TOTP invalide. Veuillez réessayer."})

    user.totp_secret = secret
    user.is_2fa_enabled = True
    user.save(update_fields=['totp_secret', 'is_2fa_enabled'])


def disable_2fa(user, password: str):
    """Désactive le 2FA pour l'utilisateur après vérification de son mot de passe."""
    if not user.check_password(password):
        raise ValidationError({"password": "Mot de passe incorrect."})

    user.totp_secret = None
    user.is_2fa_enabled = False
    user.save(update_fields=['totp_secret', 'is_2fa_enabled'])