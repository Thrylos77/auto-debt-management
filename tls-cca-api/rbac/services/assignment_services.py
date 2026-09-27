"""Role and group assignment domain services."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from audit.services import AuditService
from rbac.models import Group, GroupMembership, Role, RoleAssignment
from rbac.policies.assignment_policy import AssignmentPolicy

User = get_user_model()


def assign_role(*, actor, user, role):
    if not AssignmentPolicy.can_assign_role(actor, role):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.assign", resource=role, status="denied", reason="Forbidden", metadata={"target_user_id": user.pk})
        raise PermissionError("Not allowed to assign this role.")
    with transaction.atomic():
        assignment, created = RoleAssignment.objects.get_or_create(user=user, role=role, defaults={"created_by_id": actor.pk})
        if created:
            AuditService.record_on_commit(actor=actor, category="AUTHORIZATION", action="role.assign", resource=role, status="success", metadata={"target_user_id": user.pk})
    return assignment, created


def remove_role(*, actor, user, role):
    if not AssignmentPolicy.can_remove_role(actor, role):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="role.remove", resource=role, status="denied", reason="Forbidden", metadata={"target_user_id": user.pk})
        raise PermissionError("Not allowed to remove this role.")
    with transaction.atomic():
        assignment = RoleAssignment.objects.filter(user=user, role=role).first()
        if assignment is None:
            return False
        assignment.delete()
        AuditService.record_on_commit(actor=actor, category="AUTHORIZATION", action="role.remove", resource=role, status="success", metadata={"target_user_id": user.pk})
    return True


def add_user_to_group(*, actor, group, users):
    users = list(users)
    if not AssignmentPolicy.can_add_group_member(actor, group):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.members_add", resource=group, status="denied", reason="Forbidden", metadata={"target_user_ids": [u.pk for u in users]})
        raise PermissionError("Not allowed to add members to this group.")
    with transaction.atomic():
        added, skipped, added_ids = [], [], []
        for user in users:
            _, created = GroupMembership.objects.get_or_create(user=user, group=group, defaults={"created_by_id": actor.pk})
            (added if created else skipped).append(user.username)
            if created:
                added_ids.append(user.pk)
        if added:
            AuditService.record_on_commit(actor=actor, category="AUTHORIZATION", action="group.members_add", resource=group, status="success", metadata={"user_ids": added_ids})
    return added, skipped


def remove_user_from_group(*, actor, group, users):
    users = list(users)
    if not AssignmentPolicy.can_remove_group_member(actor, group):
        AuditService.record(actor=actor, category="AUTHORIZATION", action="group.members_remove", resource=group, status="denied", reason="Forbidden", metadata={"target_user_ids": [u.pk for u in users]})
        raise PermissionError("Not allowed to remove members from this group.")
    with transaction.atomic():
        removed, skipped, removed_ids = [], [], []
        for user in users:
            deleted, _ = GroupMembership.objects.filter(user=user, group=group).delete()
            (removed if deleted else skipped).append(user.username)
            if deleted:
                removed_ids.append(user.pk)
        if removed:
            AuditService.record_on_commit(actor=actor, category="AUTHORIZATION", action="group.members_remove", resource=group, status="success", metadata={"user_ids": removed_ids})
    return removed, skipped


def assign_role_to_user(*, actor, user_id, role_id):
    return assign_role(actor=actor, user=get_object_or_404(User, pk=user_id), role=get_object_or_404(Role, pk=role_id))


def remove_role_from_user(*, actor, user_id, role_id):
    return remove_role(actor=actor, user=get_object_or_404(User, pk=user_id), role=get_object_or_404(Role, pk=role_id))
