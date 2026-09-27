import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from audit.models import AuditEvent
from rbac.models import Permission, Role, RoleAssignment
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_audit_list_requires_audit_list_permission():
    user = User.objects.create_user(username="audit-api", email="audit-api@example.com", password="x")
    client = APIClient(); client.force_authenticate(user=user)
    assert client.get(reverse("audit-events-list")).status_code == 403

@pytest.mark.django_db
def test_audit_list_allows_reader_and_is_read_only():
    user = User.objects.create_user(username="audit-reader", email="audit-reader@example.com", password="x")
    perm = Permission.objects.create(code="audit.list", label="Audit list")
    role = Role.objects.create(name="audit-reader-role")
    role.permissions.add(perm)
    RoleAssignment.objects.create(user=user, role=role)
    AuditEvent.objects.create(category="SYSTEM", action="visible", status="success")
    client = APIClient(); client.force_authenticate(user=user)
    response = client.get(reverse("audit-events-list"))
    assert response.status_code == 200
    assert response.data["results"]
    assert client.post(reverse("audit-events-list"), {}).status_code in {405, 403}
