import base64
import hashlib
import io
import secrets
from datetime import timedelta

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from users.events import user_twofa_disabled, user_twofa_enabled, user_twofa_failure, user_twofa_success
from users.models import RecoveryCode, TwoFAChallenge, TwoFASetup, UserSecurityProfile

SETUP_LIFETIME_MINUTES = 10
CHALLENGE_LIFETIME_MINUTES = 5
MAX_ATTEMPTS = 5


def _fernet() -> Fernet:
    raw = getattr(settings, "TOTP_ENCRYPTION_KEY", "")
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
    else:
        digest = hashlib.sha256(str(settings.SECRET_KEY).encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValidationError({"detail": "Unable to decrypt the 2FA secret."}) from exc


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(user, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email or user.username,
        issuer_name=settings.TOTP_ISSUER,
    )


def generate_qr_code_base64(uri: str) -> str:
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def verify_totp_code(secret: str, code: str) -> bool:
    if not secret or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


class TwoFAService:
    @transaction.atomic
    def setup(self, user):
        profile = self._profile(user)
        if profile.two_factor_enabled or user.is_2fa_enabled:
            raise ValidationError({"detail": "2FA is already enabled."})

        TwoFASetup.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        secret = generate_totp_secret()
        raw_token = secrets.token_urlsafe(32)
        setup = TwoFASetup.objects.create(
            user=user,
            secret_encrypted=encrypt_secret(secret),
            setup_token_hash=make_password(raw_token),
            expires_at=timezone.now() + timedelta(minutes=SETUP_LIFETIME_MINUTES),
        )
        uri = get_totp_uri(user, secret)
        return {
            "setup_token": f"{setup.pk}.{raw_token}",
            "secret": secret,
            "uri": uri,
            "qrcode": generate_qr_code_base64(uri),
            "expires_at": setup.expires_at,
        }

    def verify_setup(self, user, setup_token, code, *, request=None):
        try:
            setup_id, raw_token = setup_token.split(".", 1)
        except ValueError as exc:
            raise ValidationError({"setup_token": "Invalid or expired setup token."}) from exc

        failure = False
        recovery_codes = None
        with transaction.atomic():
            setup = TwoFASetup.objects.select_for_update().filter(
                pk=setup_id,
                user=user,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if not setup or not check_password(raw_token, setup.setup_token_hash):
                raise ValidationError({"setup_token": "Invalid or expired setup token."})
            if setup.attempts >= MAX_ATTEMPTS:
                raise ValidationError({"code": "Too many invalid attempts."})

            secret = decrypt_secret(setup.secret_encrypted)
            if not verify_totp_code(secret, code):
                setup.attempts += 1
                setup.save(update_fields=["attempts"])
                failure = True
            else:
                profile = self._profile(user)
                profile.two_factor_enabled = True
                profile.totp_secret_encrypted = setup.secret_encrypted
                profile.last_security_event_at = timezone.now()
                profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted", "last_security_event_at"])

                user.is_2fa_enabled = True
                user.totp_secret = None
                user.save(update_fields=["totp_secret", "is_2fa_enabled"])

                setup.used_at = timezone.now()
                setup.save(update_fields=["used_at"])
                recovery_codes = self.generate_recovery_codes(user)

        if failure:
            user_twofa_failure.send(sender=user.__class__, user=user, request=request)
            raise ValidationError({"code": "Invalid TOTP code."})

        user_twofa_enabled.send(sender=user.__class__, user=user, request=request)
        return recovery_codes

    @transaction.atomic
    def create_login_challenge(self, user):
        TwoFAChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        raw_token = secrets.token_urlsafe(32)
        challenge = TwoFAChallenge.objects.create(
            user=user,
            token_hash=make_password(raw_token),
            expires_at=timezone.now() + timedelta(minutes=CHALLENGE_LIFETIME_MINUTES),
        )
        return f"{challenge.pk}.{raw_token}", challenge.expires_at

    def verify_login_challenge(self, challenge_token, code_or_recovery, *, request=None):
        try:
            challenge_id, raw_token = challenge_token.split(".", 1)
        except ValueError as exc:
            raise ValidationError({"challenge_token": "Invalid or expired 2FA challenge."}) from exc

        failure = False
        recovery_used = False
        user = None
        with transaction.atomic():
            challenge = TwoFAChallenge.objects.select_for_update().select_related("user").filter(
                pk=challenge_id,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if challenge is None or not check_password(raw_token, challenge.token_hash):
                raise ValidationError({"challenge_token": "Invalid or expired 2FA challenge."})
            if challenge.attempts >= MAX_ATTEMPTS:
                raise ValidationError({"code": "Too many invalid attempts."})

            user = challenge.user
            profile = self._profile(user)
            secret = decrypt_secret(profile.totp_secret_encrypted) if profile.totp_secret_encrypted else user.totp_secret
            valid = verify_totp_code(secret, code_or_recovery)
            if not valid:
                recovery = (
                    RecoveryCode.objects.select_for_update()
                    .filter(user=user, used_at__isnull=True, revoked_at__isnull=True)
                    .order_by("-created_at")
                )
                for recovery_code in recovery[:20]:
                    if check_password(code_or_recovery, recovery_code.code_hash):
                        recovery_code.used_at = timezone.now()
                        recovery_code.save(update_fields=["used_at"])
                        valid = True
                        recovery_used = True
                        break

            if not valid:
                challenge.attempts += 1
                challenge.save(update_fields=["attempts"])
                failure = True
            else:
                challenge.used_at = timezone.now()
                challenge.save(update_fields=["used_at"])

        if failure:
            user_twofa_failure.send(sender=user.__class__, user=user, request=request)
            raise ValidationError({"code": "Invalid TOTP or recovery code."})

        user_twofa_success.send(sender=user.__class__, user=user, recovery_code=recovery_used, request=request)
        return user

    @transaction.atomic
    def disable(self, user, password, *, request=None):
        if not user.check_password(password):
            raise ValidationError({"password": "Incorrect password."})
        profile = self._profile(user)
        profile.two_factor_enabled = False
        profile.totp_secret_encrypted = None
        profile.last_security_event_at = timezone.now()
        profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted", "last_security_event_at"])
        user.totp_secret = None
        user.is_2fa_enabled = False
        user.save(update_fields=["totp_secret", "is_2fa_enabled"])
        TwoFAChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        TwoFASetup.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        RecoveryCode.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        user_twofa_disabled.send(sender=user.__class__, user=user, request=request)

    @transaction.atomic
    def generate_recovery_codes(self, user, count=10):
        RecoveryCode.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        raw_codes = [secrets.token_hex(5).upper() for _ in range(count)]
        RecoveryCode.objects.bulk_create([
            RecoveryCode(user=user, code_hash=make_password(code)) for code in raw_codes
        ])
        return raw_codes

    @staticmethod
    def _profile(user):
        profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
        if profile.totp_secret_encrypted is None and getattr(user, "totp_secret", None):
            profile.totp_secret_encrypted = encrypt_secret(user.totp_secret)
            profile.two_factor_enabled = bool(user.is_2fa_enabled)
            profile.last_security_event_at = timezone.now()
            profile.save(update_fields=["totp_secret_encrypted", "two_factor_enabled", "last_security_event_at"])
            user.totp_secret = None
            user.save(update_fields=["totp_secret"])
        return profile
