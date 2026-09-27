"""Notification service and preference regression tests."""

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)
from notifications.services import NotificationService
from users.models import User


@pytest.mark.django_db
class TestNotificationService:
    def test_security_notification_ignores_user_opt_out(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        user = User.objects.create_user(
            username="security-user",
            email="security@example.com",
            password="ValidPass123!",
        )
        NotificationPreference.objects.create(
            user=user,
            business_enabled=False,
            marketing_enabled=False,
            system_enabled=False,
        )

        NotificationService.notify_password_reset_otp(
            user=user,
            otp="123456",
        )

        assert Notification.objects.filter(
            user=user,
            category=Notification.SECURITY,
        ).count() == 1
        delivery = NotificationDelivery.objects.get(
            notification__user=user,
            channel=NotificationDelivery.CHANNEL_EMAIL,
        )
        assert delivery.status == NotificationDelivery.STATUS_SENT
        assert len(mail.outbox) == 1

    def test_business_notification_can_be_disabled(self):
        user = User.objects.create_user(
            username="business-user",
            email="business@example.com",
            password="ValidPass123!",
        )
        NotificationPreference.objects.create(
            user=user,
            business_enabled=False,
        )

        result = NotificationService.notify(
            user=user,
            category=Notification.BUSINESS,
            code="business.test",
            title="Business",
            message="Business notification",
        )

        assert result is None
        assert not Notification.objects.filter(user=user).exists()

    def test_security_notifications_without_idempotency_are_not_collapsed(self, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        user = User.objects.create_user(
            username="security-repeat",
            email="security-repeat@example.com",
            password="ValidPass123!",
        )

        first = NotificationService.notify_password_reset_otp(
            user=user,
            otp="111111",
        )
        second = NotificationService.notify_password_reset_otp(
            user=user,
            otp="222222",
        )

        assert first.pk != second.pk
        assert Notification.objects.filter(
            user=user,
            category=Notification.SECURITY,
        ).count() == 2
        assert len(mail.outbox) == 2

    def test_unknown_notification_channel_is_rejected(self):
        user = User.objects.create_user(
            username="unknown-channel",
            email="unknown-channel@example.com",
            password="ValidPass123!",
        )

        with pytest.raises(ValidationError):
            NotificationService.notify(
                user=user,
                category=Notification.SYSTEM,
                code="system.test",
                title="System",
                message="Test",
                channels=("sms",),
            )

    def test_idempotency_prevents_duplicate_notification(self):
        user = User.objects.create_user(
            username="idempotent-user",
            email="idempotent@example.com",
            password="ValidPass123!",
        )
        first = NotificationService.notify(
            user=user,
            category=Notification.SYSTEM,
            code="system.test",
            title="System",
            message="Test",
            idempotency_key="system-test-1",
        )
        second = NotificationService.notify(
            user=user,
            category=Notification.SYSTEM,
            code="system.test",
            title="System",
            message="Test",
            idempotency_key="system-test-1",
        )

        assert first.pk == second.pk
        assert Notification.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestNotificationAPI:
    def test_user_cannot_read_another_users_notification(self):
        owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="ValidPass123!",
        )
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="ValidPass123!",
        )
        notification = NotificationService.notify(
            user=owner,
            category=Notification.SYSTEM,
            code="system.test",
            title="Private",
            message="Owner only",
        )

        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get(
            reverse(
                "notification-detail",
                kwargs={"pk": notification.pk},
            )
        )

        assert response.status_code == 404

    def test_mark_all_as_read(self):
        user = User.objects.create_user(
            username="read-all",
            email="read-all@example.com",
            password="ValidPass123!",
        )
        NotificationService.notify(
            user=user,
            category=Notification.SYSTEM,
            code="system.one",
            title="One",
            message="One",
        )
        NotificationService.notify(
            user=user,
            category=Notification.SYSTEM,
            code="system.two",
            title="Two",
            message="Two",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(reverse("notification-read-all"))

        assert response.status_code == 200
        assert response.data["updated"] == 2
        assert not Notification.objects.filter(user=user, is_read=False).exists()

    def test_preferences_api_can_update_non_security_preferences(self):
        user = User.objects.create_user(
            username="preferences-user",
            email="preferences@example.com",
            password="ValidPass123!",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            reverse("notification-preferences"),
            {
                "business_enabled": False,
                "marketing_enabled": True,
                "system_enabled": False,
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["business_enabled"] is False
        assert response.data["marketing_enabled"] is True
        assert response.data["system_enabled"] is False

        preference = NotificationPreference.objects.get(user=user)
        assert preference.business_enabled is False
        assert preference.marketing_enabled is True
        assert preference.system_enabled is False
