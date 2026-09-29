"""Serializers for configuration read and write operations."""

from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from configuration.models import SystemSetting
from configuration.registry import get_setting_definition
from configuration.services.type_codec import ConfigurationTypeCodec


class SystemSettingSerializer(serializers.ModelSerializer):
    """Expose the decoded, typed value while keeping metadata read-only."""

    value = serializers.SerializerMethodField()
    updated_by = serializers.StringRelatedField()

    class Meta:
        model = SystemSetting
        fields = (
            "id",
            "key",
            "category",
            "value",
            "description",
            "value_type",
            "is_public",
            "scope",
            "scope_ref",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.JSONField())
    def get_value(self, obj):
        value = ConfigurationTypeCodec.decode(obj.value, obj.value_type)
        if isinstance(value, Decimal):
            return str(value)
        return value


class SystemSettingWriteSerializer(serializers.Serializer):
    """Validate the input payload before the service applies registry rules."""

    value = serializers.JSONField()
    description = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False)

    def validate(self, attrs):
        key = self.context["key"]
        definition = get_setting_definition(key)
        if definition is None:
            raise serializers.ValidationError({"key": "Unknown configuration key."})

        try:
            encoded = ConfigurationTypeCodec.encode(
                attrs["value"],
                definition.value_type,
            )
            decoded = ConfigurationTypeCodec.decode(
                encoded,
                definition.value_type,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"value": str(exc)}) from exc

        if definition.validator is not None:
            try:
                definition.validator(decoded)
            except ValueError as exc:
                raise serializers.ValidationError({"value": str(exc)}) from exc

        attrs["value"] = decoded
        return attrs
