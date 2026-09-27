from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class Login2FASerializer(serializers.Serializer):
    challenge_token = serializers.CharField()
    code = serializers.CharField(max_length=32, min_length=6)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=100, required=False, allow_blank=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
