"""Password lifecycle services."""

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core.events import user_password_changed
from users.models import PasswordResetChallenge, UserSecurityProfile


class PasswordService:
    @transaction.atomic
    def change_password(
        self,
        user,
        new_password,
        *,
        old_password=None,
        actor=None,
        force=False,
        request=None,
        validate=True,
    ):
        """Change a password and invalidate every existing session."""
        if old_password is not None and not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Incorrect old password."})
        if user.check_password(new_password):
            raise serializers.ValidationError(
                {"new_password": "The new password must be different from the old password."}
            )
        if validate:
            validate_password(new_password, user=user)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        PasswordResetChallenge.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
        profile.last_password_change_at = timezone.now()
        profile.last_security_event_at = timezone.now()
        profile.save(update_fields=["last_password_change_at", "last_security_event_at"])

        from .session_service import SessionService

        SessionService().revoke_all_sessions(
            user,
            actor=actor or user,
            request=request,
        )
        user_password_changed.send(
            sender=user.__class__,
            user=user,
            actor=actor,
            force=force,
            request=request,
        )
        return user

    def change_own_password(
        self,
        user,
        old_password,
        new_password,
        totp_code,
        *,
        request=None,
    ):
        """Change the authenticated user's password after TOTP verification."""
        from .twofa_service import TwoFAService

        from users.models import AccountStatus

        if (
            not user.is_active
            or user.account_status != AccountStatus.ACTIVE
            or not user.has_usable_password()
            or not TwoFAService().verify_totp_for_user(user, totp_code)
        ):
            raise serializers.ValidationError({"totp_code": "Invalid TOTP code."})
        return self.change_password(
            user,
            new_password,
            old_password=old_password,
            actor=user,
            request=request,
        )
