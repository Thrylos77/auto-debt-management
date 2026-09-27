"""RBAC API serializers."""

import json
from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from core.mixins.serializers import HistoricalChangesMixin
from rbac.models import Group, Permission, Role
from rbac.services import group_services, role_services

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    class Meta:
        model = Permission
        fields = ("id", "code", "label", "description", "namespace", "is_system")
        read_only_fields = ("id", "code", "namespace", "is_system")


class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "description", "is_system", "is_assignable", "is_default", "managed_by_config")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.StringRelatedField(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Permission.objects.all(), source="permissions", write_only=True, required=False)
    class Meta:
        model = Role
        fields = ("id", "name", "description", "permissions", "permission_ids", "is_system", "is_assignable", "is_default", "managed_by_config")
        read_only_fields = ("id", "is_system", "managed_by_config")

    def create(self, validated_data):
        return role_services.create_role(actor=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return role_services.update_role(actor=self.context["request"].user, role=instance, **validated_data)


class RoleAssignmentSerializer(serializers.Serializer):
    role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source="role")


class GroupListSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)
    class Meta:
        model = Group
        fields = ("id", "name", "description", "roles", "is_system")


class GroupSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), source="roles", write_only=True, required=False)
    class Meta:
        model = Group
        fields = ("id", "name", "description", "roles", "role_ids", "is_system")
        read_only_fields = ("id", "is_system")

    def create(self, validated_data):
        return group_services.create_group(actor=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return group_services.update_group(actor=self.context["request"].user, group=instance, **validated_data)


class UserGroupAssignmentSerializer(serializers.Serializer):
    user_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")
        read_only_fields = fields


class HistoricalPermissionSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Permission.history.model
        fields = ("history_id", "history_date", "history_type_display", "history_user", "changes", "code", "label", "description", "namespace", "is_system")


class HistoricalRoleSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    permissions = serializers.SerializerMethodField()
    class Meta:
        model = Role.history.model
        fields = ("history_id", "history_date", "history_type_display", "history_user", "changes", "name", "permissions", "is_system", "is_assignable", "is_default", "managed_by_config")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        try: return json.loads(obj.history_change_reason or "{}").get("permissions", [])
        except (json.JSONDecodeError, TypeError): return []


class HistoricalGroupSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    roles = serializers.SerializerMethodField()
    class Meta:
        model = Group.history.model
        fields = ("history_id", "history_date", "history_type_display", "history_user", "changes", "name", "roles", "is_system")

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        try: return json.loads(obj.history_change_reason or "{}").get("roles", [])
        except (json.JSONDecodeError, TypeError): return []
