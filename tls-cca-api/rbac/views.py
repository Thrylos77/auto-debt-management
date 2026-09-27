"""RBAC API views."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from rbac.models import Group, Permission, Role
from rbac.policies.permission_policy import AutoPermissionMixin
from rbac.serializers import (
    GroupListSerializer, GroupSerializer, HistoricalGroupSerializer, HistoricalPermissionSerializer,
    HistoricalRoleSerializer, PermissionSerializer, RoleAssignmentSerializer, RoleListSerializer,
    RoleSerializer, UserGroupAssignmentSerializer, UserMinimalSerializer,
)
from rbac.services import assignment_services, group_services, role_services

User = get_user_model()


class PermissionListView(AutoPermissionMixin, generics.ListAPIView):
    queryset = Permission.objects.all().order_by("code")
    serializer_class = PermissionSerializer
    resource = "permission"


class PermissionRetrieveUpdateView(AutoPermissionMixin, generics.RetrieveUpdateAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    resource = "permission"

    def perform_update(self, serializer):
        instance = serializer.save()
        from audit.services import AuditService
        AuditService.record(actor=self.request.user, category="ADMINISTRATION", action="permission.update", resource=instance, status="success")


class RoleListCreateView(AutoPermissionMixin, generics.ListCreateAPIView):
    queryset = Role.objects.prefetch_related("permissions").all().order_by("name")
    resource = "role"

    def get_serializer_class(self):
        return RoleSerializer if self.request.method == "POST" else RoleListSerializer

    def perform_create(self, serializer):
        try: serializer.save()
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc


class RoleRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    resource = "role"

    def perform_update(self, serializer):
        try: serializer.save()
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc

    def perform_destroy(self, instance):
        try: role_services.delete_role(actor=self.request.user, role=instance)
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc


class GroupListCreateView(AutoPermissionMixin, generics.ListCreateAPIView):
    queryset = Group.objects.prefetch_related("roles__permissions").all().order_by("name")
    resource = "group"

    def get_serializer_class(self):
        return GroupSerializer if self.request.method == "POST" else GroupListSerializer

    def perform_create(self, serializer):
        try: serializer.save()
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc


class GroupRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.prefetch_related("roles__permissions").all()
    serializer_class = GroupSerializer
    resource = "group"

    def perform_update(self, serializer):
        try: serializer.save()
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc

    def perform_destroy(self, instance):
        try: group_services.delete_group(actor=self.request.user, group=instance)
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc


class GroupUsersListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = UserMinimalSerializer
    resource = "group"
    permission_code_map = {"GET": "view"}

    def get_queryset(self):
        return User.objects.filter(group_memberships__group_id=self.kwargs["group_id"]).order_by("username")


class BaseRoleAssignmentView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = RoleAssignmentSerializer
    resource = "rbac"
    action_type = "assign"
    permission_code_map = {"POST": "assign_role"}

    def post(self, request, user_id):
        target = get_object_or_404(User, pk=user_id)
        serializer = self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        try:
            if self.action_type == "assign":
                _, changed = assignment_services.assign_role(actor=request.user, user=target, role=role)
            else:
                changed = assignment_services.remove_role(actor=request.user, user=target, role=role)
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc
        message = "Role assigned." if self.action_type == "assign" else "Role removed."
        return Response({"detail": message if changed else ("Role already assigned." if self.action_type == "assign" else "Role was not assigned.")}, status=status.HTTP_200_OK)


class AddUserToGroupView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = UserGroupAssignmentSerializer
    resource = "rbac"
    permission_code_map = {"POST": "add_user_group"}

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        serializer = self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        try: added, skipped = assignment_services.add_user_to_group(actor=request.user, group=group, users=serializer.validated_data["user_ids"])
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc
        return Response({"added": added, "skipped": skipped})


class RemoveUserFromGroupView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = UserGroupAssignmentSerializer
    resource = "rbac"
    permission_code_map = {"POST": "remove_user_group"}

    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        serializer = self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        try: removed, skipped = assignment_services.remove_user_from_group(actor=request.user, group=group, users=serializer.validated_data["user_ids"])
        except PermissionError as exc: raise PermissionDenied(str(exc)) from exc
        return Response({"removed": removed, "skipped": skipped})


class BaseHistoryListView(generics.ListAPIView):
    model = None
    get_all = False
    def get_queryset(self):
        if self.get_all: return self.model.history.all().order_by("-history_date")
        return self.model.history.filter(id=self.kwargs["pk"]).order_by("-history_date")


class PermissionHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    serializer_class = HistoricalPermissionSerializer; model = Permission; resource = "permission_history"


class AllPermissionHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    serializer_class = HistoricalPermissionSerializer; get_all = True; model = Permission; resource = "permission_history"


class RoleHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    serializer_class = HistoricalRoleSerializer; model = Role; resource = "role_history"


class AllRoleHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalRoleSerializer; resource = "role_history"; queryset = Role.history.all().order_by("-history_date")


class GroupHistoryListView(AutoPermissionMixin, BaseHistoryListView):
    serializer_class = HistoricalGroupSerializer; model = Group; resource = "group_history"


class AllGroupHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalGroupSerializer; resource = "group_history"; queryset = Group.history.all().order_by("-history_date")


class AssignRoleToUserView(BaseRoleAssignmentView):
    action_type = "assign"
    permission_code_map = {"POST": "assign_role"}


class RemoveRoleFromUserView(BaseRoleAssignmentView):
    action_type = "remove"
    permission_code_map = {"POST": "remove_role"}
