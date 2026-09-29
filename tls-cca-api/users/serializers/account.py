"""Account-level serializers for preferences, sessions, and TOTP setup."""

from rest_framework import serializers

from users.models import UserPreference, UserSession


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = (
            "language",
            "timezone",
            "theme",
            "email_notifications",
            "system_notifications",
            "session_timeout_minutes",
        )


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = (
            "id",
            "created_at",
            "last_seen_at",
            "expires_at",
            "revoked_at",
            "ip_address",
            "user_agent",
            "device_name",
            "platform",
        )
        read_only_fields = fields


class Enable2FASerializer(serializers.Serializer):
    """Empty request used to start an authenticated enrollment."""

    pass


class VerifySetup2FASerializer(serializers.Serializer):
    setup_token = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SessionActionResponseSerializer(serializers.Serializer):
    """Generic response used by session management action endpoints."""

    detail = serializers.CharField()
