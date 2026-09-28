import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from rbac.models import Group, GroupMembership, Permission, Role, RoleAssignment
from rbac.policies.role_policy import RolePolicy
from rbac.services.permission_resolver import PermissionResolver

User = get_user_model()

@pytest.mark.django_db
def test_permission_resolver_aggregates_v2_assignments_and_groups():
    user = User.objects.create_user(username="resolver-v2", email="resolver-v2@example.com", password="x")
    direct_perm = Permission.objects.create(code="customer.view", label="Customer view")
    group_perm = Permission.objects.create(code="customer.create", label="Customer create")
    direct_role = Role.objects.create(name="resolver-direct")
    direct_role.permissions.add(direct_perm)
    group_role = Role.objects.create(name="resolver-group")
    group_role.permissions.add(group_perm)
    RoleAssignment.objects.create(user=user, role=direct_role)
    group = Group.objects.create(name="resolver-group-members")
    group.roles.add(group_role)
    GroupMembership.objects.create(user=user, group=group)
    assert PermissionResolver.get_codes(user) == {"customer.view", "customer.create"}

@pytest.mark.django_db
def test_superuser_has_all_permissions():
    user = User.objects.create_superuser(username="resolver-root", email="resolver-root@example.com", password="x")
    Permission.objects.create(code="arbitrary.view", label="Arbitrary view")
    assert PermissionResolver.has(user, "arbitrary.view")

@pytest.mark.django_db
def test_role_assignment_prevents_privilege_escalation():
    actor = User.objects.create_user(username="assigner-v2", email="assigner-v2@example.com", password="x")
    assign = Permission.objects.create(code="rbac.assign_role", label="Assign role")
    extra = Permission.objects.create(code="customer.delete", label="Customer delete")
    actor_role = Role.objects.create(name="assigner-v2-role")
    actor_role.permissions.add(assign)
    RoleAssignment.objects.create(user=actor, role=actor_role)
    target_role = Role.objects.create(name="danger-v2-role")
    target_role.permissions.add(extra)
    assert not RolePolicy.can_assign(actor, target_role)

@pytest.mark.django_db
def test_role_assignment_unique_constraint():
    user = User.objects.create_user(username="unique-v2", email="unique-v2@example.com", password="x")
    role = Role.objects.create(name="unique-v2-role")
    RoleAssignment.objects.create(user=user, role=role)
    with pytest.raises(IntegrityError):
        RoleAssignment.objects.create(user=user, role=role)


@pytest.mark.django_db
def test_denied_role_assignment_is_audited():
    from audit.models import AuditEvent
    from rbac.services.assignment_services import assign_role

    actor = User.objects.create_user(username="denied-audit", email="denied-audit@example.com", password="x")
    target = User.objects.create_user(username="denied-target", email="denied-target@example.com", password="x")
    role = Role.objects.create(name="denied-role")
    with pytest.raises(PermissionError):
        assign_role(actor=actor, user=target, role=role)
    assert AuditEvent.objects.filter(action="role.assign", status="denied", actor_user=actor).exists()


@pytest.mark.django_db
def test_permission_resolver_uses_only_canonical_assignments():
    from django.contrib.auth import get_user_model
    from rbac.models import Group, GroupMembership, Permission, Role, RoleAssignment
    from rbac.services.permission_resolver import PermissionResolver

    User = get_user_model()
    user = User.objects.create_user(
        username="canonical-rbac",
        email="canonical-rbac@example.com",
        password="x",
    )
    direct_permission = Permission.objects.create(
        code="customer.view",
        label="customer.view",
    )
    group_permission = Permission.objects.create(
        code="portfolio.view",
        label="portfolio.view",
    )
    direct_role = Role.objects.create(name="DIRECT_CANONICAL")
    direct_role.permissions.add(direct_permission)
    group_role = Role.objects.create(name="GROUP_CANONICAL")
    group_role.permissions.add(group_permission)
    group = Group.objects.create(name="GROUP_CANONICAL")
    group.roles.add(group_role)

    RoleAssignment.objects.create(user=user, role=direct_role)
    GroupMembership.objects.create(user=user, group=group)

    assert PermissionResolver.get_codes(user) == {
        "customer.view",
        "portfolio.view",
    }
