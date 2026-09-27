"""Configuration API tests."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from configuration.models import SystemSetting
from users.models import User


@pytest.mark.django_db
class TestConfigurationAPI:
    def test_admin_can_list_settings(self):
        user = User.objects.create_superuser(
            username="config-admin",
            email="config-admin@example.com",
            password="ValidPass123!",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("configuration-settings-list"))

        assert response.status_code == 200
        assert any(
            item["key"] == "customer_inactivity_duration_months"
            for item in response.data["results"]
        )

    def test_admin_can_update_setting(self):
        user = User.objects.create_superuser(
            username="config-update",
            email="config-update@example.com",
            password="ValidPass123!",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            reverse(
                "configuration-setting-detail",
                kwargs={"key": "customer_inactivity_duration_months"},
            ),
            {"value": 36},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["value"] == 36
        assert SystemSetting.objects.get(
            key="customer_inactivity_duration_months"
        ).value == "36"

    def test_regular_user_cannot_list_settings_without_permission(self):
        user = User.objects.create_user(
            username="config-reader",
            email="config-reader@example.com",
            password="ValidPass123!",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("configuration-settings-list"))

        assert response.status_code == 403
