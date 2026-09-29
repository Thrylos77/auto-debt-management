"""Secure self-service and administrator-triggered password recovery."""

from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.events import (
    user_password_reset_completed,
    user_password_reset_requested,
)
from notifications.services import NotificationService
from rbac.services.permission_resolver import PermissionResolver
from users.models import AccountStatus, PasswordResetChallenge, UserSecurityProfile
from users.services.password_service import PasswordService
from users.services.twofa_service import TwoFAService
from users.security_utils import generate_token, hash_token

RESET_LIFETIME_MINUTES = 30

class PasswordRecoveryService:
    @transaction.atomic
    def issue(
        self,
        user,
        *,
        requested_by=None,
        purpose=PasswordResetChallenge.SELF_SERVICE,
        request=None,
    ):
        """Issue a fresh, single-use password reset challenge."""
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"detail": "Disabled accounts cannot reset their password."})
        if purpose == PasswordResetChallenge.ADMIN_TRIGGERED:
            if requested_by is None or not PermissionResolver.has(
                requested_by,
                "user.security.reset_password",
            ):
                raise ValidationError(
                    {"detail": "Administrative password reset is not permitted."}
                )
        if purpose == PasswordResetChallenge.SELF_SERVICE and (
            not user.is_active
            or user.account_status != AccountStatus.ACTIVE
            or user.is_staff
            or user.is_superuser
            or PermissionResolver.has(user, "user.security.reset_password")
            or PermissionResolver.has(user, "user.security.reset_2fa")
        ):
            raise ValidationError({"detail": "Privileged accounts require administrative recovery."})

        profile = UserSecurityProfile.objects.filter(user=user).first()
        if purpose == PasswordResetChallenge.SELF_SERVICE and (
            not profile or not profile.two_factor_enabled
        ):
            raise ValidationError({"detail": "This account requires administrative recovery."})

        PasswordResetChallenge.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        raw_token = generate_token()
        challenge = PasswordResetChallenge.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=RESET_LIFETIME_MINUTES),
            requested_by=requested_by,
        )

        NotificationService.notify_password_reset_link(
            user=user,
            token=raw_token,
            admin_triggered=purpose == PasswordResetChallenge.ADMIN_TRIGGERED,
        )
        user_password_reset_requested.send(
            sender=user.__class__,
            user=user,
            actor=requested_by,
            purpose=purpose,
            request=request,
        )
        return challenge

    @transaction.atomic
    def complete(
        self,
        raw_token: str,
        new_password: str,
        *,
        totp_code: str | None = None,
        request=None,
    ):
        challenge = (
            PasswordResetChallenge.objects
            .select_for_update()
            .select_related("user")
            .filter(
                token_hash=hash_token(raw_token),
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if challenge is None:
            raise ValidationError({"token": "Invalid or expired reset token."})
        if challenge.attempts >= PasswordResetChallenge.MAX_ATTEMPTS:
            raise ValidationError({"token": "Reset attempts exceeded."})

        user = challenge.user
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"token": "This account is disabled."})

        profile = UserSecurityProfile.objects.filter(user=user).first()
        if challenge.purpose == PasswordResetChallenge.SELF_SERVICE:
            if (
                not user.is_active
                or user.account_status != AccountStatus.ACTIVE
                or not profile
                or not profile.two_factor_enabled
                or not profile.totp_secret_encrypted
            ):
                raise ValidationError({"token": "This account requires administrative recovery."})
            if not totp_code or not TwoFAService().verify_totp_for_user(user, totp_code):
                challenge.attempts += 1
                challenge.save(update_fields=["attempts"])
                raise ValidationError({"totp_code": "Invalid TOTP code."})

        validate_password(new_password, user=user)
        if user.check_password(new_password):
            raise ValidationError({"new_password": "The new password must be different from the current password."})

        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])

        PasswordService().change_password(
            user,
            new_password,
            actor=challenge.requested_by or user,
            force=True,
            request=request,
            validate=False,
        )

        # A disabled account remains disabled even when an administrator has
        # triggered a password recovery for it.
        if user.account_status != AccountStatus.DISABLED:
            if profile and profile.two_factor_enabled:
                user.account_status = AccountStatus.ACTIVE
                user.is_active = True
            else:
                user.account_status = AccountStatus.PASSWORD_SET
                user.is_active = False
            user.save(update_fields=["account_status", "is_active"])

        user_password_reset_completed.send(
            sender=user.__class__,
            user=user,
            actor=challenge.requested_by,
            purpose=challenge.purpose,
            request=request,
        )
        return user