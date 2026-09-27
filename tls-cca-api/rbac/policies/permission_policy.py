"""Permission policies and DRF authorization adapters."""

from rest_framework.permissions import BasePermission, IsAuthenticated

from rbac.services.permission_resolver import PermissionResolver


class HasPermission(BasePermission):
    required_permissions = ()

    @classmethod
    def with_perms(cls, *perms):
        class _HasPermission(cls):
            required_permissions = perms
        return _HasPermission

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and all(
            PermissionResolver.has(user, code) for code in self.required_permissions
        ))


class DenyPermission(BasePermission):
    def has_permission(self, request, view):
        return False


DEFAULT_ACTION_MAP = {
    "list": "list", "retrieve": "view", "create": "create",
    "update": "update", "partial_update": "update", "destroy": "delete",
    "GET": "view", "POST": "create", "PUT": "update",
    "PATCH": "update", "DELETE": "delete",
}


class AutoPermissionMixin:
    resource = None
    default_permission_classes = (IsAuthenticated,)
    permission_code_map = {}

    def get_permission_code_map(self):
        return {**DEFAULT_ACTION_MAP, **self.permission_code_map}

    def get_permissions(self):
        if getattr(self, "swagger_fake_view", False):
            return [cls() for cls in getattr(self, "permission_classes", self.default_permission_classes)]
        if not self.resource:
            return [cls() for cls in getattr(self, "permission_classes", self.default_permission_classes)]
        action_key = (
            getattr(self, "action", None)
            or getattr(self, "custom_action", None)
            or (self.request.method if hasattr(self, "request") else None)
        )
        suffix = self.get_permission_code_map().get(action_key)
        if not suffix:
            return [DenyPermission()]
        code = suffix if "." in suffix else f"{self.resource}.{suffix}"
        return [HasPermission.with_perms(code)()]


class PermissionPolicy:
    @staticmethod
    def can_manage(actor):
        return PermissionResolver.has(actor, "permission.update")

    @staticmethod
    def can_view(actor):
        return PermissionResolver.has(actor, "permission.view") or PermissionResolver.has(actor, "permission.list")
