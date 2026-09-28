"""Regression tests for dashboard and federated search endpoints."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from rbac.models import Permission, Role, RoleAssignment
from users.models import User


@pytest.fixture
def api_client():
    return APIClient()


def _user_with_permissions(*codes):
    """Create an active user with the requested RBAC permission codes."""

    user = User.objects.create_user(
        username="reporting_perm_{}".format(abs(hash(codes)) % (10**8)),
        email="reporting_perm_{}@example.com".format(abs(hash(codes)) % (10**8)),
        password="x",
        is_active=True,
    )
    role, _ = Role.objects.get_or_create(
        name="REPORTING_ROLE_{}".format(abs(hash(codes)) % (10**8))
    )

    for code in codes:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            label=code,
        )
        role.permissions.add(permission)

    RoleAssignment.objects.create(user=user, role=role)
    return user


@pytest.mark.django_db
class TestDashboardSummaryPermission:
    def test_summary_denied_without_permission(self, api_client):
        """An authenticated user without dashboard.summary receives 403."""

        user = _user_with_permissions("customer.view")
        api_client.force_authenticate(user=user)

        response = api_client.get(reverse("dashboard-summary"))

        assert response.status_code == 403

    def test_summary_allowed_with_permission(self, api_client):
        """The reporting dashboard keeps the dedicated summary permission."""

        user = _user_with_permissions("dashboard.summary")
        api_client.force_authenticate(user=user)

        response = api_client.get(reverse("dashboard-summary"))

        assert response.status_code == 200
        assert "total_sales" in response.data
        assert "recovery_rate" in response.data

    def test_summary_works_with_empty_decimal_aggregates(self, api_client):
        """Empty DecimalField aggregates must not raise mixed-type errors."""

        user = _user_with_permissions("dashboard.summary")
        api_client.force_authenticate(user=user)

        response = api_client.get(reverse("dashboard-summary"))

        assert response.status_code == 200
        assert response.data["total_sales"] == 0.0
        assert response.data["total_debt_initial"] == 0.0
        assert response.data["total_debt_balance"] == 0.0
        assert response.data["total_recovered"] == 0.0


@pytest.mark.django_db
def test_global_search_keeps_short_queries_empty(api_client, new_user):
    """Global search should not query business tables for one-character input."""

    api_client.force_authenticate(user=new_user)

    response = api_client.get(reverse("global-search"), {"q": "a"})

    assert response.status_code == 200
    assert response.data == {
        "sales": [],
        "debts": [],
        "customers": [],
    }


def test_reporting_root_routes_are_exposed_by_v1_urls():
    assert reverse("dashboard-summary") == "/api/v1/dashboard/summary/"
    assert reverse("global-search") == "/api/v1/search/"
