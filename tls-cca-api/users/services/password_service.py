from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from users.events import user_password_changed
from users.models import UserSecurityProfile


class PasswordService:
    @transaction.atomic
    def change_password(self, user, new_password, *, old_password=None, actor=None, force=False, request=None):
        if old_password is not None and not user.check_password(old_password):
            raise serializers.ValidationError({"old_password": "Incorrect old password."})
        if user.check_password(new_password):
            raise serializers.ValidationError({"new_password": "The new password must be different from the old password."})
        validate_password(new_password, user=user)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
        profile.last_password_change_at = timezone.now()
        profile.save(update_fields=["last_password_change_at"])

        from .session_service import SessionService
        SessionService().revoke_all_sessions(user, actor=actor or user, request=request)
        user_password_changed.send(sender=user.__class__, user=user, actor=actor, force=force, request=request)
        return user

    def change_own_password(self, user, old_password, new_password, *, request=None):
        return self.change_password(user, new_password, old_password=old_password, actor=user, request=request)

    def request_reset(self, user, otp_code, new_password):
        from .otp_service import reset_password_with_otp
        return reset_password_with_otp(user, otp_code, new_password)
