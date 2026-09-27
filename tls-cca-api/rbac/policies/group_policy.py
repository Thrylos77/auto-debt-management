"""Policies for group operations and privilege escalation."""

from rbac.services.permission_resolver import PermissionResolver


def group_role_permission_codes(group):
    return set(group.roles.values_list("permissions__code", flat=True))


class GroupPolicy:
    @staticmethod
    def can_create(actor):
        return actor.is_superuser or PermissionResolver.has(actor, "group.create")

    @staticmethod
    def can_update(actor, group):
        return bool(actor.is_superuser or (not group.is_system and PermissionResolver.has(actor, "group.update")))

    @staticmethod
    def can_delete(actor, group):
        return bool(actor.is_superuser or (not group.is_system and PermissionResolver.has(actor, "group.delete")))

    @staticmethod
    def can_add_members(actor, group):
        return bool(actor.is_superuser or (PermissionResolver.has(actor, "rbac.add_user_group") and group_role_permission_codes(group) <= PermissionResolver.get_codes(actor)))

    @staticmethod
    def can_remove_members(actor, group):
        return actor.is_superuser or PermissionResolver.has(actor, "rbac.remove_user_group")
