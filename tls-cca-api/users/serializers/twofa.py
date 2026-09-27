from rest_framework import serializers


class Enable2FASerializer(serializers.Serializer):
    pass


class VerifySetup2FASerializer(serializers.Serializer):
    setup_token = serializers.CharField()
    code = serializers.CharField(max_length=6, min_length=6)


class Disable2FASerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
