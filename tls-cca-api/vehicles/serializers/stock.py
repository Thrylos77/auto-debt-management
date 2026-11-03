"""Serializers for stock locations and movement history."""

from rest_framework import serializers

from vehicles.models import StockLocation, StockMovement


class StockLocationSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockLocation
        fields = (
            "id",
            "code",
            "name",
            "type",
            "address",
            "is_active",
            "vehicle_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "vehicle_count", "created_at", "updated_at")


class TransferVehicleSerializer(serializers.Serializer):
    to_location = serializers.PrimaryKeyRelatedField(queryset=StockLocation.objects.filter(is_active=True))
    reason = serializers.CharField(required=False, allow_blank=True)


class ReceiveVehicleSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(queryset=StockLocation.objects.filter(is_active=True))
    reason = serializers.CharField(required=False, allow_blank=True)


class VehicleStatusReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class StockMovementSerializer(serializers.ModelSerializer):
    vehicle_reference = serializers.CharField(source="vehicle.stock_reference", read_only=True)
    from_location_name = serializers.CharField(source="from_location.name", read_only=True)
    to_location_name = serializers.CharField(source="to_location.name", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "vehicle",
            "vehicle_reference",
            "movement_type",
            "from_location",
            "from_location_name",
            "to_location",
            "to_location_name",
            "reference_type",
            "reference_id",
            "reason",
            "performed_by",
            "performed_by_name",
            "occurred_at",
            "metadata",
        )
        read_only_fields = fields
