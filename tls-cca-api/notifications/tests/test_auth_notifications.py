"""Regression tests for authentication security notifications."""

import pytest
from django.core import mail

from notifications.models import Notification, NotificationDelivery
from notifications.services import NotificationService
from users.models import User


@pytest.mark.django_db
def test_account_invitation_email_contains_frontend_link(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.AUTH_PUBLIC_BASE_URL = "http://localhost:3000"
    settings.AUTH_INVITATION_PATH = "/auth/invitation"
    user = User.objects.create_user(
        username="invite-mail",
        email="invite-mail@example.com",
        password="x",
    )

    NotificationService.notify_account_invitation(
        user=user,
        token="invite-token",
    )

    assert len(mail.outbox) == 1
    assert "http://localhost:3000/auth/invitation?token=invite-token" in mail.outbox[0].body
    notification = Notification.objects.get(user=user, code="account_invitation")
    assert "invite-token" not in str(notification.data)


def _assert_email_sent(user, code):
    delivery = NotificationDelivery.objects.get(
        notification__user=user,
        notification__code=code,
        channel=NotificationDelivery.CHANNEL_EMAIL,
    )
    assert delivery.status == NotificationDelivery.STATUS_SENT


@pytest.mark.django_db
def test_security_recovery_notifications_are_always_delivered(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user = User.objects.create_user(
        username="security-mail",
        email="security-mail@example.com",
        password="x",
    )

    NotificationService.notify_password_reset_link(
        user=user,
        token="password-token",
    )
    NotificationService.notify_password_reset_link(
        user=user,
        token="admin-token",
        admin_triggered=True,
    )
    NotificationService.notify_twofa_reset(
        user=user,
        token="1.setup-token",
    )

    assert len(mail.outbox) == 3
    _assert_email_sent(user, "password_reset_link")
    _assert_email_sent(user, "password_reset_link_admin")
    _assert_email_sent(user, "twofa_reset")
