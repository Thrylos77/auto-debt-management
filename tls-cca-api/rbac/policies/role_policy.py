"""Policies for role operations and privilege escalation."""

from rbac.services.permission_resolver import PermissionResolver


def role_permission_codes(role):
    return set(role.permissions.values_list("code", flat=True))


class RolePolicy:
    @staticmethod
    def can_create(actor):
        return actor.is_superuser or PermissionResolver.has(actor, "role.create")

    @staticmethod
    def can_update(actor, role):
        return bool(actor.is_superuser or (not role.is_system and PermissionResolver.has(actor, "role.update")))

    @staticmethod
    def can_delete(actor, role):
        return bool(actor.is_superuser or (not role.is_system and PermissionResolver.has(actor, "role.delete")))

    @staticmethod
    def can_assign(actor, role):
        if actor.is_superuser:
            return True
        return bool(
            role.is_assignable
            and not role.is_system
            and PermissionResolver.has(actor, "rbac.assign_role")
            and role_permission_codes(role) <= PermissionResolver.get_codes(actor)
        )
