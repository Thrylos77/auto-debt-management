from .twofa_service import (
    TwoFAService, decrypt_secret, encrypt_secret, generate_qr_code_base64,
    generate_totp_secret, get_totp_uri, verify_totp_code,
)


def enable_2fa(user, secret, code):
    """Compatibility adapter for old callers that still pass the setup secret."""
    service = TwoFAService()
    from users.models import TwoFASetup
    from django.contrib.auth.hashers import make_password
    from django.utils import timezone
    from datetime import timedelta
    import secrets
    token = secrets.token_urlsafe(32)
    TwoFASetup.objects.create(
        user=user,
        secret_encrypted=encrypt_secret(secret),
        setup_token_hash=make_password(token),
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    return service.verify_setup(user, token, code)


def disable_2fa(user, password):
    return TwoFAService().disable(user, password)
