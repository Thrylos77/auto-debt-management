import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_liveness_endpoint():
    response = APIClient().get(reverse("health-live"))
    assert response.status_code == 200
    assert response.data["status"] == "ok"


@pytest.mark.django_db
def test_readiness_endpoint_uses_database():
    response = APIClient().get(reverse("health-ready"))
    assert response.status_code == 200
    assert response.data["checks"]["database"] == "ok"


@pytest.mark.django_db
def test_correlation_id_is_returned():
    response = APIClient().get(reverse("health-live"), HTTP_X_CORRELATION_ID="test-correlation-123")
    assert response.status_code == 200
    assert response["X-Correlation-ID"] == "test-correlation-123"


def test_platform_apps_are_registered():
    from django.conf import settings

    assert "configuration.apps.ConfigurationConfig" in settings.INSTALLED_APPS
    assert "notifications.apps.NotificationsConfig" in settings.INSTALLED_APPS
