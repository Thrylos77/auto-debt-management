import json
from rest_framework import serializers
from .models import Group, Role, Permission
from .services import group_services, role_services
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from core.serializers.mixins import HistoricalChangesMixin

User = get_user_model()

# ----- Serializers -----
class PermissionSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)  # Make 'code' read-only to prevent changes after creation
    class Meta:
        model = Permission
        fields = ('id', 'code', 'label', 'description')

class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'description')

class RoleSerializer(serializers.ModelSerializer):
    # For READ (GET): Displays full, nested Permission objects.
    permissions = serializers.StringRelatedField(many=True, read_only=True)
    # For WRITE (POST, PUT, PATCH): Accepts a list of permission IDs.
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Permission.objects.all(), 
        write_only=True, 
        source='permissions', # This field updates the 'permissions' model relationship
        help_text="List of permission IDs to associate with this role."
    )

    class Meta:
        model = Role
        # 'permissions' is for output (read), 'permission_ids' is for input (write).
        fields = ('id', 'name', 'description', 'permissions', 'permission_ids')

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        return role_services.create_role(validated_data['name'], validated_data['description'], permissions)

class RoleAssignmentSerializer(serializers.Serializer):
    # Serializer for the role assignment/removal endpoints.
    role_id = serializers.IntegerField(required=True, help_text="The ID of the role to assign or remove.")

# --- Group Serializers ---
class GroupListSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'roles']

class GroupSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True, read_only=True)  # Nested roles for read
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), write_only=True, source="roles"
    )
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'roles', 'role_ids']

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])
        return group_services.create_group(validated_data['name'], validated_data['description'], roles)

class UserGroupAssignmentSerializer(serializers.Serializer):
    users = serializers.StringRelatedField(many=True, read_only=True)
    user_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(),
        write_only=True,
        help_text="IDs of the users to assign or remove."
    )
    def to_representation(self, instance):
        return {
            "id": instance.id,
            "name": instance.name,
            "users": [user.username for user in instance.users.all()]
        }

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')
        read_only_fields = fields

# ----- Historical Serializers -----
class HistoricalPermissionSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Permission.history.model
        fields = (
            'history_id', 'history_date', 'history_type_display', 'history_user',
            'changes', 'code', 'label', 'description'
        )


class HistoricalRoleSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role.history.model
        fields = (
            'history_id', 'history_date', 'history_type_display', 'history_user',
            'changes', 'name', 'permissions',
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_permissions(self, obj):
        """
        Retrieves the snapshot of permission codes stored in the history record.
        The snapshot is saved by the `add_permissions_snapshot` signal into the
        `history_change_reason` field as a JSON string.
        """
        if not obj.history_change_reason:
            return []
        try:
            data = json.loads(obj.history_change_reason)
            return data.get('permissions', [])
        except (json.JSONDecodeError, TypeError):
            return []


class HistoricalGroupSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Group.history.model
        fields = (
            'history_id', 'history_date', 'history_type_display', 'history_user',
            'changes', 'name', 'roles',
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, obj):
        if not obj.history_change_reason:
            return []
        try:
            data = json.loads(obj.history_change_reason)
            return data.get('roles', [])
        except (json.JSONDecodeError, TypeError):
            return []