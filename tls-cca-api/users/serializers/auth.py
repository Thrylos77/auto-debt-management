"""Authentication and account-onboarding serializers."""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class Login2FASerializer(serializers.Serializer):
    challenge_token = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class VerifyInvitationTwoFASerializer(serializers.Serializer):
    setup_token = serializers.CharField(write_only=True)
    code = serializers.CharField(min_length=6, max_length=6, write_only=True)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class TwoFARecoverySetupSerializer(serializers.Serializer):
    setup_token = serializers.CharField(write_only=True)


class TwoFARecoveryVerifySerializer(serializers.Serializer):
    setup_token = serializers.CharField(write_only=True)
    code = serializers.CharField(min_length=6, max_length=6, write_only=True)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)
