"""rbac/tests/test_views.py"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rbac.models import Role, Permission

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestRBACViews:
    def test_list_roles(self, api_client, new_user):
        """Test listing roles."""
        Role.objects.create(name="Manager")
        url = reverse('role-list-create')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_retrieve_role(self, api_client, new_user):
        """Test retrieving a specific role."""
        role = Role.objects.create(name="Supervisor")
        url = reverse('role-rud', kwargs={'pk': role.pk})
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['name'] == "Supervisor"

    def test_list_permissions(self, api_client, new_user):
        """Test listing permissions."""
        Permission.objects.create(code="test.perm", label="Test Perm")
        url = reverse('permission-list')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0