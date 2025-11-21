# Generic DRF permissions
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated

class HasPermission(BasePermission):
    # Custom permission to check if the user has a specific permission code.
    required_permissions = []

    @classmethod
    def with_perms(cls, *perms):
        class _HasPermission(cls):
            required_permissions = perms
        return _HasPermission

    def has_permission(self, request, view):
        user = request.user 
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or all(user.has_permission(perm) for perm in self.required_permissions)

DEFAULT_ACTION_MAP = {
    # DRF ViewSets / GenericAPIView "actions"
    'list': 'list',
    'retrieve': 'view',
    'create': 'create',
    'update': 'update',
    'partial_update': 'update',
    'destroy': 'delete',
    # Fallback APIView HTTP methods
    'GET': 'view',
    'POST': 'create',
    'PUT': 'update',
    'PATCH': 'update',
    'DELETE': 'delete',
}

class PermissionCodeMixin:
    permission_code_map = {}

    def get_required_permission(self):
        action = self.action
        return self.get_permission_code_map().get(action)

class AutoPermissionMixin:
    """
    Automatically maps DRF actions or HTTP methods to permissions.
    Example: "user.list", "user.retrieve", "user.update", etc.
    """
    resource = None
    default_permission_classes = (IsAuthenticated,)
    permission_code_map = {}  # Map of permission codes to their names in any app

    def get_permission_code_map(self):
        # Merge DEFAULT_ACTION_MAP with view-specific permission_code_map
        return {**DEFAULT_ACTION_MAP, **self.permission_code_map}

    def get_permissions(self):
        # If the view is a fake swagger view, return the default permissions
        if getattr(self, 'swagger_fake_view', False):
            return [cls() for cls in getattr(self, 'permission_classes', self.default_permission_classes)]

        if not self.resource:
            return [cls() for cls in getattr(self, 'permission_classes', self.default_permission_classes)]

        # Determine the "action" key
        action_key = (
            getattr(self, 'action', None) or 
            getattr(self, 'custom_action', None)   # custom action if defined
            or (self.request.method if hasattr(self, 'request') else None)
        )

        # 1 : Try merged map (custom overrides default)
        perm_cod_map = self.get_permission_code_map()
        perm_suffix = perm_cod_map.get(action_key)

         # If custom code already fully qualified, use as is
        if perm_suffix:
            return [HasPermission.with_perms(f"{self.resource}.{perm_suffix}")()]

        
        # 2 : Fallback to default permission classes
        return [cls() for cls in getattr(self, 'permission_classes', self.default_permission_classes)]

