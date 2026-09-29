"""Notification orchestration across in-app and email channels."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from notifications.channels import EmailChannel, InAppChannel
from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)


class NotificationService:
    """Create notifications and dispatch them through approved channels."""

    CHANNELS = {
        NotificationDelivery.CHANNEL_IN_APP: InAppChannel,
        NotificationDelivery.CHANNEL_EMAIL: EmailChannel,
    }

    @classmethod
    def _preference_enabled(cls, user, category: str) -> bool:
        # Security notifications are always forced and cannot be disabled by a
        # user preference.
        if category == Notification.SECURITY:
            return True

        preference, _ = NotificationPreference.objects.get_or_create(user=user)
        if category == Notification.BUSINESS:
            return preference.business_enabled
        if category == Notification.MARKETING:
            return preference.marketing_enabled
        if category == Notification.SYSTEM:
            return preference.system_enabled
        return False

    @classmethod
    @transaction.atomic
    def notify(
        cls,
        *,
        user,
        category,
        code,
        title,
        message,
        channels=(NotificationDelivery.CHANNEL_IN_APP,),
        resource=None,
        data=None,
        idempotency_key=None,
        context=None,
    ):
        """Create one notification and deliver it through selected channels."""

        if not cls._preference_enabled(user, category):
            return None

        invalid_channels = [
            channel_name
            for channel_name in channels
            if channel_name not in cls.CHANNELS
        ]
        if invalid_channels:
            raise ValidationError(
                {
                    "channels": (
                        "Unsupported notification channel(s): "
                        + ", ".join(sorted(invalid_channels))
                    )
                }
            )

        defaults = {
            "category": category,
            "code": code,
            "title": title,
            "message": message,
            "resource_type": (
                resource.__class__.__name__
                if resource is not None
                else ""
            ),
            "resource_id": (
                str(getattr(resource, "pk", ""))
                if resource is not None
                else ""
            ),
            "data": data or {},
        }

        if idempotency_key is None:
            notification = Notification.objects.create(
                user=user,
                **defaults,
            )
            created = True
        else:
            notification, created = Notification.objects.get_or_create(
                user=user,
                idempotency_key=idempotency_key,
                defaults=defaults,
            )

        if not created:
            return notification

        for channel_name in channels:
            channel_class = cls.CHANNELS[channel_name]
            delivery, _ = NotificationDelivery.objects.get_or_create(
                notification=notification,
                channel=channel_name,
            )
            channel_class().send(
                notification,
                delivery,
                context=context,
            )

        return notification

    @classmethod
    def _frontend_link(cls, path, token):
        base = getattr(settings, "AUTH_PUBLIC_BASE_URL", "")
        return f"{base.rstrip('/')}{path}?token={token}"

    @classmethod
    def notify_account_invitation(cls, *, user, token):
        return cls.notify(
            user=user,
            category=Notification.SECURITY,
            code="account_invitation",
            title="Complete your TLS CCA account setup",
            message="Use your invitation link to define your password and enroll your Authenticator.",
            channels=(NotificationDelivery.CHANNEL_EMAIL,),
            context={
                "link": cls._frontend_link(
                    getattr(
                        settings,
                        "AUTH_INVITATION_PATH",
                        "/auth/invitation",
                    ),
                    token,
                )
            },
        )

    @classmethod
    def notify_password_reset_link(cls, *, user, token, admin_triggered=False):
        return cls.notify(
            user=user,
            category=Notification.SECURITY,
            code=(
                "password_reset_link_admin"
                if admin_triggered
                else "password_reset_link"
            ),
            title="Password reset request",
            message="A secure password reset link has been generated for your account.",
            channels=(NotificationDelivery.CHANNEL_EMAIL,),
            context={
                "link": cls._frontend_link(
                    getattr(
                        settings,
                        "AUTH_PASSWORD_RESET_PATH",
                        "/auth/password/reset",
                    ),
                    token,
                )
            },
        )

    @classmethod
    def notify_twofa_reset(cls, *, user, token):
        return cls.notify(
            user=user,
            category=Notification.SECURITY,
            code="twofa_reset",
            title="Authenticator reset",
            message="Your Authenticator has been reset and must be enrolled again.",
            channels=(NotificationDelivery.CHANNEL_EMAIL,),
            context={
                "link": cls._frontend_link(
                    getattr(
                        settings,
                        "AUTH_TWOFA_RECOVERY_PATH",
                        "/auth/2fa/recovery",
                    ),
                    token,
                )
            },
        )

    @staticmethod
    def mark_as_read(notification: Notification) -> Notification:
        """Mark one in-app notification as read."""

        if notification.is_read:
            return notification
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
        return notification

    @staticmethod
    def mark_all_as_read(user) -> int:
        """Mark all unread notifications of one user as read."""

        now = timezone.now()
        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).update(
            is_read=True,
            read_at=now,
        )
