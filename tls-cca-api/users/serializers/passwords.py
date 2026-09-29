from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class ChangeOwnPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(min_length=6, max_length=6, write_only=True)

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(
        min_length=6,
        max_length=6,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    def validate_new_password(self, value):
        validate_password(value, user=None)
        return value


class EmptyPasswordResetSerializer(serializers.Serializer):
    """Placeholder serializer for administrator-triggered reset endpoints."""

    pass
