from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Group, Role, Permission
from .serializers import *
from .permission_control import AutoPermissionMixin
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_view, extend_schema

User = get_user_model()

# ----- Permissions CRUD -----

@extend_schema(tags=["Permissions"])
class PermissionListView(AutoPermissionMixin, generics.ListAPIView):
    queryset = Permission.objects.all().order_by('code')
    serializer_class = PermissionSerializer
    resource = "permission"

@extend_schema(tags=["Permissions"])
class PermissionRetrieveUpdateView(AutoPermissionMixin, generics.RetrieveUpdateAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    resource = "permission"

# ----- Roles CRUD -----
@extend_schema(tags=["Roles"])
class RoleListCreateView(AutoPermissionMixin, generics.ListCreateAPIView):
    queryset = Role.objects.all().order_by('name')
    resource = "role"

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoleSerializer
        return RoleListSerializer

@extend_schema(tags=["Roles"])
class RoleRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.prefetch_related('permissions').all()
    serializer_class = RoleSerializer
    resource = "role"

# ----- Groups CRUD -----
@extend_schema(tags=["Groups"])
class GroupListCreateView(AutoPermissionMixin, generics.ListCreateAPIView):
    queryset = Group.objects.all().order_by('name')
    resource = "group"

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GroupSerializer
        return GroupListSerializer

@extend_schema(tags=["Groups"])
class GroupRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.prefetch_related('roles').all()
    serializer_class = GroupSerializer
    resource = "group"

@extend_schema(tags=["Groups"])
class GroupUsersListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = UserMinimalSerializer
    lookup_url_kwarg = 'group_id'
    resource = 'group'

    def get_queryset(self):
        group = Group.objects.prefetch_related('users').get(id=self.kwargs['group_id'])
        return group.users.all()

# ----- Assign/Add & Remove -----
class BaseRoleAssignmentView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = RoleAssignmentSerializer
    queryset = User.objects.all().order_by('username')
    lookup_url_kwarg = 'user_id'
    resource = 'rbac'
    action_type = None  # "assign" or "remove"
    permission_suffix = None  # ex: "assign_role" or "remove_role"

    def get_permission_code_map(self):
        return {'POST': f"{self.permission_suffix}"}

    def post(self, request, user_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_id = serializer.validated_data['role_id']

        user = self.get_object()
        role = get_object_or_404(Role, pk=role_id)

        if self.action_type == "assign":
            if user.roles.filter(pk=role.pk).exists():
                return Response(
                    {"detail": "This user already has the specified role."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.roles.add(role)
            message = f"Role '{role.name}' assigned to user '{user.username}'."

        elif self.action_type == "remove":
            if not user.roles.filter(pk=role.pk).exists():
                return Response(
                    {"detail": "This user does not have the specified role."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.roles.remove(role)
            message = f"Role '{role.name}' removed from user '{user.username}'."

        return Response({"detail": message}, status=status.HTTP_200_OK)

class BaseUserGroupView(AutoPermissionMixin, generics.GenericAPIView):
    """
    Base class to handle adding/removing a user to/from a group.
    Subclasses define the `action` attribute as 'add' or 'remove'.
    """
    serializer_class = UserGroupAssignmentSerializer
    queryset = Group.objects.all()
    lookup_url_kwarg = 'group_id'
    resource = 'rbac'
    action_type = None  # 'add' or 'remove'
    permission_suffix = None  # ex: "add_user_group" or "remove_user_group"

    def get_permission_code_map(self):
        return {'POST': f"{self.permission_suffix}"}

    def post(self, request, group_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = self.get_object()
        users = serializer.validated_data['user_ids']

        existing_ids = set(group.users.values_list('id', flat=True))
        added, skipped = [], []

        for user in users:
            in_group = user.id in existing_ids
            if self.action_type == 'add' and not in_group:
                group.users.add(user)
                added.append(user.username)
            elif self.action_type == 'remove' and in_group:
                group.users.remove(user)
                added.append(user.username)
            else:
                skipped.append(user.username)

        status_code = 200 if added else 409
        action_word = "added" if self.action_type == 'add' else "removed"
        message = f"Users {action_word}: {added}" if added else f"No users {action_word}; skipped: {skipped}"

        return Response({"detail": message}, status=status_code)

@extend_schema(tags=["Assignments"])
class AssignRoleToUserView(BaseRoleAssignmentView):
    action_type = "assign"
    permission_suffix = "assign_role"

@extend_schema(tags=["Assignments"])
class RemoveRoleFromUserView(BaseRoleAssignmentView):
    action_type = "remove"
    permission_suffix = "remove_role"


@extend_schema(tags=["Assignments"])
class AddUserToGroupView(BaseUserGroupView):
    action_type = 'add'
    permission_suffix = "add_user_group"

@extend_schema(tags=["Assignments"])
class RemoveUserFromGroupView(BaseUserGroupView):
    action_type = 'remove'
    permission_suffix = "remove_user_group"



# ----- Historical Read -----

class BaseHistoryListView(generics.ListAPIView):
    """
    Base view to handle historical listing by primary key (for single object)
    or for all objects if `get_all` is set to True.
    """
    model = None  # Must be defined in subclass
    get_all = False

    def get_queryset(self):
        if self.get_all:
            return self.model.history.all().order_by('-history_date')
        obj_pk = self.kwargs['pk']
        return self.model.history.filter(id=obj_pk).order_by('-history_date')

    # Permissions
@extend_schema(tags=["Permissions"])
class PermissionHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    # Retrieves the change history for a specific permission.
    serializer_class = HistoricalPermissionSerializer
    model = Permission
    resource = "permission_history"


@extend_schema_view(get=extend_schema(operation_id="all_permission_history", tags=["Permissions"]))
class AllPermissionHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    serializer_class = HistoricalPermissionSerializer
    get_all = True
    model = Permission
    resource = "permission_history"

    # Roles
@extend_schema(tags=["Roles"])
class RoleHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    # Retrieves the change history for a specific role.
    serializer_class = HistoricalRoleSerializer
    model = Role
    resource = "role_history"

@extend_schema_view(get=extend_schema(operation_id="all_role_history", tags=["Roles"]))
class AllRoleHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalRoleSerializer
    resource = "role_history"
    queryset = Role.history.all().order_by('-history_date')

    # Groups
@extend_schema(tags=["Groups"])
class GroupHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    # Retrieves the change history for a specific Group.
    serializer_class = HistoricalGroupSerializer
    model = Group
    resource = "group_history"

@extend_schema_view(get=extend_schema( operation_id="all_group_history" ))
@extend_schema(tags=["Groups"])
class AllGroupHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalGroupSerializer
    resource = "group_history"
    queryset = Group.history.all().order_by('-history_date')