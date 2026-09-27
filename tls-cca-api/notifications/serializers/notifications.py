"""Notification API serializers."""

from rest_framework import serializers

from notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "category",
            "code",
            "title",
            "message",
            "resource_type",
            "resource_id",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "business_enabled",
            "marketing_enabled",
            "system_enabled",
            "updated_at",
        )
        read_only_fields = ("updated_at",)
