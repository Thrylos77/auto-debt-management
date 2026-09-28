from rest_framework import serializers

from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field

from users.models import User
from users.services.user_service import create_user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "phone", "birthday", "address", "is_active")
        read_only_fields = ("id", "is_active")


class OwnProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "phone", "birthday", "address")
        read_only_fields = ("id", "username", "email")


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "birthday", "address", "email", "phone", "password")
        read_only_fields = ("id",)
        extra_kwargs = {"password": {"write_only": True}}

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return create_user(validated_data)


class HistoricalUserSerializer(serializers.ModelSerializer):
    history_user = serializers.StringRelatedField()
    history_type_display = serializers.CharField(source="get_history_type_display", read_only=True)
    changes = serializers.SerializerMethodField()

    class Meta:
        model = User.history.model
        fields = [
            "history_id", "history_date", "history_type_display", "history_user", "changes",
            "username", "email", "last_name", "is_active",
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_changes(self, obj):
        if obj.history_type == "~" and obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            changes = []
            for change in delta.changes:
                if change.field == "date_joined":
                    continue
                if change.field == "password":
                    changes.append({"field": "password", "old": "********", "new": "********"})
                else:
                    changes.append({"field": change.field, "old": change.old, "new": change.new})
            return changes
        return None


class EmptyRequestSerializer(serializers.Serializer):
    """Placeholder serializer for endpoints that intentionally take no body."""

    pass


class SessionActionResponseSerializer(serializers.Serializer):
    """Generic response used by session management action endpoints."""

    detail = serializers.CharField()
