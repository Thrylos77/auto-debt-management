from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from users.models import User
from users.services.user_service import create_user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "birthday",
            "address",
            "is_active",
            "account_status",
        )
        read_only_fields = ("id", "is_active", "account_status")


class OwnProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "birthday",
            "address",
        )
        read_only_fields = ("id", "username", "email")


class RegisterSerializer(serializers.ModelSerializer):
    """Admin-created accounts start in the invitation onboarding state."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "birthday",
            "address",
            "email",
            "phone",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        request = self.context.get("request")
        return create_user(
            validated_data,
            actor=getattr(request, "user", None),
            request=request,
        )


class HistoricalUserSerializer(serializers.ModelSerializer):
    history_user = serializers.StringRelatedField()
    history_type_display = serializers.CharField(
        source="get_history_type_display",
        read_only=True,
    )
    changes = serializers.SerializerMethodField()

    class Meta:
        model = User.history.model
        fields = [
            "history_id",
            "history_date",
            "history_type_display",
            "history_user",
            "changes",
            "username",
            "email",
            "last_name",
            "is_active",
            "account_status",
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
                    changes.append(
                        {
                            "field": "password",
                            "old": "********",
                            "new": "********",
                        }
                    )
                else:
                    changes.append(
                        {
                            "field": change.field,
                            "old": change.old,
                            "new": change.new,
                        }
                    )
            return changes
        return None


class EmptyRequestSerializer(serializers.Serializer):
    """Placeholder serializer for endpoints that intentionally take no body."""

    pass

