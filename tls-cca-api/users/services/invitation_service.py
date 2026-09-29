"""Invitation lifecycle for newly created user accounts."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.events import user_invitation_created, user_password_initialized
from notifications.services import NotificationService
from users.models import AccountInvitation, AccountStatus, UserSecurityProfile
from users.security_utils import generate_token, hash_token
from users.services.twofa_service import TwoFAService

INVITATION_LIFETIME_HOURS = 48


class InvitationService:
    @transaction.atomic
    def issue(self, user, *, actor=None, request=None):
        """Invalidate previous invitations and send a fresh invitation email."""
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"detail": "Disabled accounts cannot receive invitations."})
        if user.account_status == AccountStatus.ACTIVE and user.is_active:
            raise ValidationError({"detail": "Active accounts do not need an invitation."})

        AccountInvitation.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=timezone.now())

        raw_token = generate_token()
        invitation = AccountInvitation.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            expires_at=timezone.now() + timedelta(hours=INVITATION_LIFETIME_HOURS),
            created_by=actor,
        )

        NotificationService.notify_account_invitation(
            user=user,
            token=raw_token,
        )
        user_invitation_created.send(
            sender=user.__class__,
            user=user,
            actor=actor,
            request=request,
        )
        return invitation

    @transaction.atomic
    def accept(self, raw_token: str, new_password: str, *, request=None):
        invitation = (
            AccountInvitation.objects
            .select_for_update()
            .select_related("user")
            .filter(
                token_hash=hash_token(raw_token),
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if invitation is None:
            raise ValidationError({"token": "Invalid or expired invitation."})
        if invitation.attempts >= AccountInvitation.MAX_ATTEMPTS:
            raise ValidationError({"token": "Invitation attempts exceeded."})

        user = invitation.user
        if user.account_status == AccountStatus.DISABLED:
            raise ValidationError({"token": "This account is disabled."})
        if user.account_status == AccountStatus.ACTIVE:
            raise ValidationError({"token": "This account is already active."})

        from django.contrib.auth.password_validation import validate_password

        validate_password(new_password, user=user)
        user.set_password(new_password)
        user.is_active = False
        user.account_status = AccountStatus.PASSWORD_SET
        user.save(update_fields=["password", "is_active", "account_status"])

        profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
        profile.last_password_change_at = timezone.now()
        profile.last_security_event_at = timezone.now()
        profile.save(update_fields=["last_password_change_at", "last_security_event_at"])

        invitation.used_at = timezone.now()
        invitation.save(update_fields=["used_at"])

        user_password_initialized.send(
            sender=user.__class__,
            user=user,
            request=request,
        )

        setup = TwoFAService().setup(user)
        return {**setup, "two_factor_required": True}
