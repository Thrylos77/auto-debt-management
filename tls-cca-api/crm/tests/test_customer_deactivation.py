"""crm/tests/test_customer_deactivation.py"""
import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import Customer
from crm.services import customer_services
from core.services import settings_services

User = get_user_model()


@pytest.mark.django_db
class TestAutoDeactivationUsesConfiguredPolicy:
    def _create_customer(self, created_at):
        customer = Customer.objects.create(phone='123456789')
        Customer.objects.filter(pk=customer.pk).update(created_at=created_at)
        customer.refresh_from_db()
        return customer

    def test_deactivates_beyond_configured_months(self):
        settings_services.set_customer_inactivity_months(2)
        now = timezone.now()

        old_customer = self._create_customer(now - timedelta(days=90))   # ~3 months ago
        recent_customer = self._create_customer(now - timedelta(days=30))  # ~1 month ago

        checked, deactivated = customer_services.auto_deactivate_inactive_customers()

        assert checked == 2
        assert deactivated == 1
        old_customer.refresh_from_db()
        recent_customer.refresh_from_db()
        assert old_customer.is_active is False
        assert recent_customer.is_active is True

    def test_default_policy_is_48_months(self):
        # No setting configured -> uses the 48-month default
        now = timezone.now()
        under_48 = self._create_customer(now - timedelta(days=40 * 30))   # ~40 months
        over_48 = self._create_customer(now - timedelta(days=60 * 30))    # ~60 months

        checked, deactivated = customer_services.auto_deactivate_inactive_customers()

        assert checked == 2
        assert deactivated == 1
        under_48.refresh_from_db()
        over_48.refresh_from_db()
        assert under_48.is_active is True
        assert over_48.is_active is False


@pytest.mark.django_db
class TestCustomerDeactivationPolicyView:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def admin(self):
        return User.objects.create_superuser(
            username='admin', email='admin@example.com', password='x'
        )

    @pytest.fixture
    def regular(self):
        return User.objects.create_user(
            username='regular', email='regular@example.com', password='x', is_active=True
        )

    def test_get_policy_as_admin(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        url = reverse('customer-deactivation-policy')
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['inactivity_months'] == 48
        assert response.data['default_inactivity_months'] == 48

    def test_update_policy_as_admin(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        url = reverse('customer-deactivation-policy')
        response = api_client.put(url, {'inactivity_months': 36}, format='json')
        assert response.status_code == 200
        assert response.data['inactivity_months'] == 36
        # Config actually persisted and used by the service
        assert settings_services.get_customer_inactivity_months() == 36

    def test_update_policy_rejects_invalid(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        url = reverse('customer-deactivation-policy')
        response = api_client.put(url, {'inactivity_months': 0}, format='json')
        assert response.status_code == 400

    def test_get_policy_rejected_for_regular_user(self, api_client, regular):
        api_client.force_authenticate(user=regular)
        url = reverse('customer-deactivation-policy')
        response = api_client.get(url)
        assert response.status_code in (403, 404)

    def test_update_policy_rejected_for_regular_user(self, api_client, regular):
        api_client.force_authenticate(user=regular)
        url = reverse('customer-deactivation-policy')
        response = api_client.put(url, {'inactivity_months': 24}, format='json')
        assert response.status_code in (403, 404)
