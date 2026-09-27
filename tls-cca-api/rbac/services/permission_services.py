"""Compatibility shim for V1 imports; authorization now lives under policies/services."""

from rbac.policies.permission_policy import AutoPermissionMixin, DenyPermission, HasPermission
from rbac.services.permission_resolver import PermissionResolver


def get_user_permissions(user):
    return PermissionResolver.get_queryset(user)
