"""TOTP enrollment, login challenges and administrative 2FA recovery."""

import base64
import hashlib
import io
import secrets
from datetime import timedelta

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.events import (
    user_twofa_enabled,
    user_twofa_failure,
    user_twofa_reset,
    user_twofa_success,
)
from notifications.services import NotificationService
from users.models import (
    AccountStatus,
    PasswordResetChallenge,
    TwoFAChallenge,
    TwoFASetup,
    UserSecurityProfile,
)
from users.security_utils import generate_token, hash_token

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
    if not secret or not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


class TwoFAService:
    @transaction.atomic
    def setup(self, user):
        profile = self._profile(user)
        if profile.two_factor_enabled:
            raise ValidationError({"detail": "2FA is already enabled."})

        TwoFASetup.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        secret = generate_totp_secret()
        raw_token = generate_token()
        setup = TwoFASetup.objects.create(
            user=user,
            secret_encrypted=encrypt_secret(secret),
            setup_token_hash=hash_token(raw_token),
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

    def get_setup_by_token(self, setup_token: str):
        setup_id, raw_token = self._split_setup_token(setup_token)
        setup = (
            TwoFASetup.objects
            .filter(
                pk=setup_id,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related("user")
            .first()
        )
        if setup is None or not self._token_matches(setup, raw_token):
            raise ValidationError({"setup_token": "Invalid or expired setup token."})
        if setup.user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"setup_token": "This account is disabled."})

        secret = decrypt_secret(setup.secret_encrypted)
        uri = get_totp_uri(setup.user, secret)
        return {
            "setup_token": setup_token,
            "secret": secret,
            "uri": uri,
            "qrcode": generate_qr_code_base64(uri),
            "expires_at": setup.expires_at,
        }

    @transaction.atomic
    def verify_setup_token(self, setup_token, code, *, request=None):
        setup_id, raw_token = self._split_setup_token(setup_token)
        setup = (
            TwoFASetup.objects
            .select_for_update()
            .select_related("user")
            .filter(
                pk=setup_id,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if setup is None or not self._token_matches(setup, raw_token):
            raise ValidationError({"setup_token": "Invalid or expired setup token."})
        if setup.attempts >= MAX_ATTEMPTS:
            raise ValidationError({"code": "Too many invalid attempts."})

        user = setup.user
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"setup_token": "This account is disabled."})

        secret = decrypt_secret(setup.secret_encrypted)
        if not verify_totp_code(secret, code):
            setup.attempts += 1
            setup.save(update_fields=["attempts"])
            transaction.on_commit(
                lambda: user_twofa_failure.send(
                    sender=user.__class__,
                    user=user,
                    request=request,
                )
            )
            raise ValidationError({"code": "Invalid TOTP code."})

        profile = self._profile(user)
        profile.two_factor_enabled = True
        profile.totp_secret_encrypted = setup.secret_encrypted
        profile.last_two_factor_enrollment_at = timezone.now()
        profile.last_security_event_at = timezone.now()
        profile.save(
            update_fields=[
                "two_factor_enabled",
                "totp_secret_encrypted",
                "last_two_factor_enrollment_at",
                "last_security_event_at",
            ]
        )

        setup.used_at = timezone.now()
        setup.save(update_fields=["used_at"])

        if user.has_usable_password():
            user.account_status = AccountStatus.ACTIVE
            user.is_active = True
        else:
            user.account_status = AccountStatus.INVITED
            user.is_active = False
        user.save(update_fields=["account_status", "is_active"])

        transaction.on_commit(
            lambda: user_twofa_enabled.send(
                sender=user.__class__,
                user=user,
                request=request,
            )
        )
        return user

    def verify_setup(self, user, setup_token, code, *, request=None):
        setup_id, _ = self._split_setup_token(setup_token)
        if not TwoFASetup.objects.filter(pk=setup_id, user=user).exists():
            raise ValidationError({"setup_token": "Invalid or expired setup token."})
        return self.verify_setup_token(setup_token, code, request=request)

    @transaction.atomic
    def create_login_challenge(self, user):
        TwoFAChallenge.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())
        raw_token = generate_token()
        challenge = TwoFAChallenge.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + timedelta(minutes=CHALLENGE_LIFETIME_MINUTES),
        )
        return f"{challenge.pk}.{raw_token}", challenge.expires_at

    @transaction.atomic
    def verify_login_challenge(self, challenge_token, code, *, request=None):
        challenge_id, raw_token = self._split_challenge_token(challenge_token)
        challenge = (
            TwoFAChallenge.objects
            .select_for_update()
            .select_related("user")
            .filter(
                pk=challenge_id,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if challenge is None or not secrets.compare_digest(
            hash_token(raw_token),
            challenge.token_hash,
        ):
            raise ValidationError({"challenge_token": "Invalid or expired 2FA challenge."})
        if challenge.attempts >= MAX_ATTEMPTS:
            raise ValidationError({"code": "Too many invalid attempts."})

        user = challenge.user
        profile = self._profile(user)
        if (
            not user.is_active
            or user.account_status != AccountStatus.ACTIVE
            or not profile.two_factor_enabled
            or not profile.totp_secret_encrypted
        ):
            raise ValidationError(
                {"challenge_token": "Invalid or expired 2FA challenge."}
            )

        secret = decrypt_secret(profile.totp_secret_encrypted)
        if not verify_totp_code(secret, code):
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            transaction.on_commit(
                lambda: user_twofa_failure.send(
                    sender=user.__class__,
                    user=user,
                    request=request,
                )
            )
            raise ValidationError({"code": "Invalid TOTP code."})

        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        transaction.on_commit(
            lambda: user_twofa_success.send(
                sender=user.__class__,
                user=user,
                request=request,
            )
        )
        return user

    @transaction.atomic
    def reset_by_admin(self, user, *, actor, request=None):
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"detail": "Disabled accounts cannot be reset here."})
        if actor is None:
            raise ValidationError({"detail": "An administrator is required."})
        from rbac.services.permission_resolver import PermissionResolver

        if not PermissionResolver.has(actor, "user.security.reset_2fa"):
            raise ValidationError(
                {"detail": "Authenticator reset is not permitted."}
            )

        profile = self._profile(user)
        profile.two_factor_enabled = False
        profile.totp_secret_encrypted = None
        profile.last_security_event_at = timezone.now()
        profile.save(
            update_fields=[
                "two_factor_enabled",
                "totp_secret_encrypted",
                "last_security_event_at",
            ]
        )

        TwoFAChallenge.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())
        TwoFASetup.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())
        PasswordResetChallenge.objects.filter(
            user=user,
            purpose=PasswordResetChallenge.SELF_SERVICE,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        from .session_service import SessionService

        SessionService().revoke_all_sessions(
            user,
            actor=actor,
            request=request,
        )

        if user.has_usable_password():
            user.account_status = AccountStatus.PASSWORD_SET
        else:
            user.account_status = AccountStatus.INVITED
        user.is_active = False
        user.save(update_fields=["account_status", "is_active"])

        setup = self.setup(user)
        NotificationService.notify_twofa_reset(
            user=user,
            token=setup["setup_token"],
        )
        transaction.on_commit(
            lambda: user_twofa_reset.send(
                sender=user.__class__,
                user=user,
                actor=actor,
                request=request,
            )
        )
        return setup

    @staticmethod
    def verify_totp_for_user(user, code) -> bool:
        profile = UserSecurityProfile.objects.filter(user=user).first()
        if not profile or not profile.two_factor_enabled:
            return False
        secret = decrypt_secret(profile.totp_secret_encrypted)
        return verify_totp_code(secret, code)

    @staticmethod
    def _profile(user):
        profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def _split_setup_token(setup_token):
        try:
            setup_id, raw_token = setup_token.split(".", 1)
        except (AttributeError, ValueError) as exc:
            raise ValidationError({"setup_token": "Invalid or expired setup token."}) from exc
        if not setup_id or not raw_token:
            raise ValidationError({"setup_token": "Invalid or expired setup token."})
        return setup_id, raw_token

    @staticmethod
    def _token_matches(setup, raw_token):
        return secrets.compare_digest(hash_token(raw_token), setup.setup_token_hash)

    @staticmethod
    def _split_challenge_token(challenge_token):
        try:
            challenge_id, raw_token = challenge_token.split(".", 1)
        except (AttributeError, ValueError) as exc:
            raise ValidationError({"challenge_token": "Invalid or expired 2FA challenge."}) from exc
        if not challenge_id or not raw_token:
            raise ValidationError({"challenge_token": "Invalid or expired 2FA challenge."})
        return challenge_id, raw_token
