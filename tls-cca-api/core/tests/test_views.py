"""core/tests/test_views.py"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient

from rbac.models import Permission, Role

User = get_user_model()


def _user_with_permissions(*codes):
    user = User.objects.create_user(
        username='core_perm_{}'.format(abs(hash(codes)) % (10 ** 8)),
        email='core_perm_{}@example.com'.format(abs(hash(codes)) % (10 ** 8)),
        password='x',
        is_active=True,
    )
    role, _ = Role.objects.get_or_create(
        name='CORE_ROLE_{}'.format(abs(hash(codes)) % (10 ** 8))
    )
    for code in codes:
        perm, _ = Permission.objects.get_or_create(code=code, label=code)
        role.permissions.add(perm)
    user.roles.add(role)
    return user


@pytest.mark.django_db
class TestDashboardSummaryPermission:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_summary_denied_without_permission(self, api_client):
        """Fail-closed: an authenticated user without dashboard.summary gets 403."""
        user = _user_with_permissions('customer.view')
        api_client.force_authenticate(user=user)
        response = api_client.get(reverse('dashboard-summary'))
        assert response.status_code == 403

    def test_summary_mapping_requires_dashboard_summary_permission(self):
        """The `summary` action maps to `dashboard.summary` (fail-closed), verified
        directly on the permission layer to avoid the pre-existing aggregation bug."""
        from rbac.services.permission_services import AutoPermissionMixin, HasPermission

        request = type('R', (), {'method': 'GET'})()
        mixin = AutoPermissionMixin()
        mixin.resource = 'dashboard'
        mixin.action = 'summary'
        mixin.request = request
        mixin.permission_code_map = {'summary': 'summary'}

        perm_classes = mixin.get_permissions()
        assert len(perm_classes) == 1
        assert isinstance(perm_classes[0], HasPermission)
        # Not a silent IsAuthenticated fallback: plain user is denied.
        plain = _user_with_permissions('customer.view')
        assert perm_classes[0].has_permission(
            type('Req', (), {'user': plain})(), None
        ) is False

        # User holding the mapped permission is accepted.
        authorized = _user_with_permissions('dashboard.summary')
        assert perm_classes[0].has_permission(
            type('Req', (), {'user': authorized})(), None
        ) is True
