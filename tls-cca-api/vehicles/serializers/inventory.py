"""Serializers for physical inventory sessions and observations."""

from rest_framework import serializers

from vehicles.models import InventoryItem, InventorySession, StockLocation, VehicleUnit


class InventorySessionSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = InventorySession
        fields = (
            "id",
            "reference",
            "location",
            "location_name",
            "status",
            "started_at",
            "completed_at",
            "started_by",
            "validated_by",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "reference",
            "status",
            "started_at",
            "completed_at",
            "started_by",
            "validated_by",
            "location_name",
            "created_at",
            "updated_at",
        )


class InventoryItemSerializer(serializers.ModelSerializer):
    vehicle_reference = serializers.CharField(source="vehicle.stock_reference", read_only=True)
    expected_location_name = serializers.CharField(source="expected_location.name", read_only=True)
    observed_location_name = serializers.CharField(source="observed_location.name", read_only=True)
    result = serializers.CharField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "session",
            "vehicle",
            "vehicle_reference",
            "expected_location",
            "expected_location_name",
            "observed_location",
            "observed_location_name",
            "expected_status",
            "observed_status",
            "found",
            "result",
            "notes",
            "scanned_reference",
            "scanned_at",
            "scanned_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "session",
            "vehicle_reference",
            "expected_location",
            "expected_location_name",
            "expected_status",
            "result",
            "found",
            "scanned_at",
            "scanned_by",
            "created_at",
            "updated_at",
        )


class InventorySessionDetailSerializer(InventorySessionSerializer):
    items = InventoryItemSerializer(many=True, read_only=True)

    class Meta(InventorySessionSerializer.Meta):
        fields = InventorySessionSerializer.Meta.fields + ("items",)


class CreateInventorySessionSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(queryset=StockLocation.objects.filter(is_active=True))
    notes = serializers.CharField(required=False, allow_blank=True)


class RecordInventoryItemSerializer(serializers.Serializer):
    vehicle = serializers.PrimaryKeyRelatedField(queryset=VehicleUnit.objects.all(), required=False)
    scanned_reference = serializers.CharField(max_length=80, required=False, allow_blank=True)
    observed_location = serializers.PrimaryKeyRelatedField(queryset=StockLocation.objects.filter(is_active=True))
    observed_status = serializers.ChoiceField(choices=VehicleUnit.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("vehicle") and not attrs.get("scanned_reference", "").strip():
            raise serializers.ValidationError(
                {"vehicle": "Provide a vehicle or a scanned stock reference."}
            )
        return attrs


class InventoryAdjustmentSerializer(serializers.Serializer):
    reason = serializers.CharField()
