"""Group domain services; no DRF Response objects here."""

from django.db import transaction

from audit.services import AuditService
from rbac.models import Group
from rbac.policies.group_policy import GroupPolicy
from rbac.services.permission_resolver import PermissionResolver


def _permission_codes(roles):
    return {code for role in roles for code in role.permissions.values_list("code", flat=True)}


def create_group(*, actor, name, description="", roles=()):
    if not GroupPolicy.can_create(actor):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.create", status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to create groups.")
    roles = list(roles)
    codes = _permission_codes(roles)
    if not actor.is_superuser and not codes <= PermissionResolver.get_codes(actor):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.create", status="denied", reason="Privilege escalation")
        raise PermissionError("A group cannot grant permissions the actor does not possess.")
    with transaction.atomic():
        group = Group.objects.create(name=name, description=description)
        group.roles.set(roles)
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="group.create", resource=group, status="success")
    return group


def update_group(*, actor, group, name=None, description=None, roles=None):
    if not GroupPolicy.can_update(actor, group):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.update", resource=group, status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to update this group.")
    roles = list(roles) if roles is not None else None
    if roles is not None:
        codes = _permission_codes(roles)
        if not actor.is_superuser and not codes <= PermissionResolver.get_codes(actor):
            AuditService.record(actor=actor, category="AUTHORIZATION", action="group.update", resource=group, status="denied", reason="Privilege escalation")
            raise PermissionError("A group cannot grant permissions the actor does not possess.")
    with transaction.atomic():
        if roles is not None:
            group.roles.set(roles)
        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        group.save()
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="group.update", resource=group, status="success")
    return group


def delete_group(*, actor, group):
    if not GroupPolicy.can_delete(actor, group):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.delete", resource=group, status="denied", reason="Forbidden")
        raise PermissionError("Not allowed to delete this group.")
    group_id, group_name = group.pk, group.name
    with transaction.atomic():
        group.delete()
        AuditService.record_on_commit(actor=actor, category="ADMINISTRATION", action="group.delete", status="success", metadata={"group_id": group_id, "group_name": group_name})
