from rest_framework import serializers

from users.models import UserSession


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = (
            "id", "created_at", "last_seen_at", "expires_at", "revoked_at",
            "ip_address", "user_agent", "device_name", "platform",
        )
        read_only_fields = fields
