"""Policies for assignment mutations."""

from rbac.policies.group_policy import GroupPolicy
from rbac.policies.role_policy import RolePolicy
from rbac.services.permission_resolver import PermissionResolver


class AssignmentPolicy:
    can_assign_role = staticmethod(RolePolicy.can_assign)

    @staticmethod
    def can_remove_role(actor, role):
        return bool(actor.is_superuser or (not role.is_system and PermissionResolver.has(actor, "rbac.remove_role")))

    can_add_group_member = staticmethod(GroupPolicy.can_add_members)
    can_remove_group_member = staticmethod(GroupPolicy.can_remove_members)
