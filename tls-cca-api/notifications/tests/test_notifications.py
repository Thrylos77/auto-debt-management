"""Notification service and preference regression tests."""

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from django.urls import reverse

from notifications.models import Notification, NotificationDelivery, NotificationPreference
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

        NotificationService.notify_password_reset_link(
            user=user,
            token="123456-token",
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

        first = NotificationService.notify_password_reset_link(
            user=user,
            token="111111-token",
        )
        second = NotificationService.notify_password_reset_link(
            user=user,
            token="222222-token",
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

    def test_notification_read_endpoints(self):
        user = User.objects.create_user(
            username="notification-api",
            email="notification-api@example.com",
            password="ValidPass123!",
        )
        first = Notification.objects.create(
            user=user,
            category=Notification.SYSTEM,
            code="system.one",
            title="One",
            message="First",
        )
        Notification.objects.create(
            user=user,
            category=Notification.SYSTEM,
            code="system.two",
            title="Two",
            message="Second",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(reverse("notification-read", kwargs={"pk": first.pk}))
        assert response.status_code == 200
        first.refresh_from_db()
        assert first.is_read is True

        response = client.post(reverse("notification-read-all"))
        assert response.status_code == 200
        assert response.data["updated"] == 1
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
