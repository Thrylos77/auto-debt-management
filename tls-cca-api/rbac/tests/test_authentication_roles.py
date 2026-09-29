"""Regression tests for security-specific user administration roles."""

import pytest

from rbac.models import Permission, Role, RoleAssignment
from rbac.services.permission_resolver import PermissionResolver
from users.models import User


def assign_role(user, role):
    RoleAssignment.objects.create(user=user, role=role)


@pytest.mark.django_db
def test_security_admin_has_both_recovery_permissions():
    user = User.objects.create_user(
        username="security-admin-role",
        email="security-admin-role@example.com",
        password="x",
    )
    role = Role.objects.create(name="SECURITY_ADMIN")
    reset_password = Permission.objects.create(
        code="user.security.reset_password",
        label="Reset password",
    )
    reset_2fa = Permission.objects.create(
        code="user.security.reset_2fa",
        label="Reset 2FA",
    )
    role.permissions.add(reset_password, reset_2fa)
    assign_role(user, role)

    assert PermissionResolver.has(user, "user.security.reset_password")
    assert PermissionResolver.has(user, "user.security.reset_2fa")


@pytest.mark.django_db
def test_user_admin_does_not_receive_2fa_reset_permission():
    user = User.objects.create_user(
        username="user-admin-role",
        email="user-admin-role@example.com",
        password="x",
    )
    role = Role.objects.create(name="USER_ADMIN")
    reset_password = Permission.objects.create(
        code="user.security.reset_password",
        label="Reset password",
    )
    reset_2fa = Permission.objects.create(
        code="user.security.reset_2fa",
        label="Reset 2FA",
    )
    role.permissions.add(reset_password)
    assign_role(user, role)

    assert PermissionResolver.has(user, "user.security.reset_password")
    assert not PermissionResolver.has(user, "user.security.reset_2fa")
