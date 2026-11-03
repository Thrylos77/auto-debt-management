"""Serializers for reservation creation and reservation history."""

from django.utils import timezone
from rest_framework import serializers

from crm.models import Customer
from vehicles.models import VehicleReservation, VehicleUnit


class CreateVehicleReservationSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.filter(is_active=True))
    expires_at = serializers.DateTimeField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Expiration must be in the future.")
        return value


class VehicleReservationSerializer(serializers.ModelSerializer):
    vehicle_reference = serializers.CharField(source="vehicle.stock_reference", read_only=True)
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    reserved_by_name = serializers.CharField(source="reserved_by.get_full_name", read_only=True)
    released_by_name = serializers.CharField(source="released_by.get_full_name", read_only=True)

    class Meta:
        model = VehicleReservation
        fields = (
            "id",
            "reference",
            "vehicle",
            "vehicle_reference",
            "customer",
            "customer_name",
            "reserved_by",
            "reserved_by_name",
            "status",
            "reserved_at",
            "expires_at",
            "released_at",
            "released_by",
            "released_by_name",
            "release_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReleaseReservationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class ConvertReservationToSaleSerializer(serializers.Serializer):
    sale_reference = serializers.CharField(max_length=120)
