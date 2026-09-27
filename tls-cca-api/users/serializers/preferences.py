from rest_framework import serializers

from users.models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = (
            "language", "timezone", "theme", "email_notifications",
            "system_notifications", "session_timeout_minutes",
        )
