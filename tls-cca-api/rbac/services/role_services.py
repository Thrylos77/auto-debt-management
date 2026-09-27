"""Role domain services; no DRF Response objects here."""

from django.db import transaction

from audit.services import AuditService
from rbac.models import Role
from rbac.policies.role_policy import RolePolicy
from rbac.services.permission_resolver import PermissionResolver


def create_role(*, actor, name, description="", permissions=()):
    if not RolePolicy.can_create(actor):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.create", status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to create roles.")
    permissions = list(permissions)
    if not actor.is_superuser and {p.code for p in permissions} - PermissionResolver.get_codes(actor):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.create", status="denied", reason="Privilege escalation")
        raise PermissionError("A role cannot grant permissions the actor does not possess.")
    with transaction.atomic():
        role = Role.objects.create(name=name, description=description)
        if permissions:
            role.permissions.set(permissions)
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="role.create", resource=role, status="success")
    return role


def update_role(*, actor, role, name=None, description=None, permissions=None):
    if not RolePolicy.can_update(actor, role):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.update", resource=role, status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to update this role.")
    permissions = list(permissions) if permissions is not None else None
    if permissions is not None and not actor.is_superuser and {p.code for p in permissions} - PermissionResolver.get_codes(actor):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.update", resource=role, status="denied", reason="Privilege escalation")
        raise PermissionError("A role cannot grant permissions the actor does not possess.")
    with transaction.atomic():
        if permissions is not None:
            role.permissions.set(permissions)
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        role.save()
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="role.update", resource=role, status="success")
    return role


def delete_role(*, actor, role):
    if not RolePolicy.can_delete(actor, role):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.delete", resource=role, status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to delete this role.")
    role_id, role_name = role.pk, role.name
    with transaction.atomic():
        role.delete()
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="role.delete", status="success", metadata={"role_id": role_id, "role_name": role_name})
