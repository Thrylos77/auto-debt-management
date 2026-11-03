"""Serializers for physical vehicle units, images and pricing."""

from decimal import Decimal

from rest_framework import serializers

from vehicles.models import VehicleImage, VehiclePriceHistory, VehicleUnit


class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = (
            "id",
            "file",
            "is_primary",
            "sort_order",
            "caption",
            "mime_type",
            "file_size",
            "checksum",
            "uploaded_by",
            "uploaded_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "mime_type",
            "file_size",
            "checksum",
            "uploaded_by",
            "uploaded_at",
            "created_at",
            "updated_at",
        )


class VehiclePriceHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = VehiclePriceHistory
        fields = (
            "id",
            "old_price",
            "new_price",
            "currency",
            "reason",
            "changed_by",
            "changed_by_name",
            "changed_at",
        )
        read_only_fields = fields


class VehicleUnitSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    model_name = serializers.CharField(source="variant.model.name", read_only=True)
    brand_name = serializers.CharField(source="variant.model.brand.name", read_only=True)
    category_name = serializers.CharField(source="variant.model.category.name", read_only=True)
    current_location_name = serializers.CharField(source="current_location.name", read_only=True)
    images = VehicleImageSerializer(many=True, read_only=True)

    class Meta:
        model = VehicleUnit
        fields = (
            "id",
            "stock_reference",
            "variant",
            "variant_name",
            "model_name",
            "brand_name",
            "category_name",
            "vin",
            "chassis_number",
            "engine_number",
            "registration_number",
            "manufacture_year",
            "model_year",
            "color",
            "condition",
            "mileage",
            "mileage_unit",
            "acquisition_date",
            "acquisition_cost",
            "currency",
            "current_price",
            "status",
            "current_location",
            "current_location_name",
            "is_catalog_visible",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "stock_reference",
            "variant_name",
            "model_name",
            "brand_name",
            "category_name",
            "status",
            "current_location",
            "current_location_name",
            "images",
            "created_at",
            "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["current_price"].read_only = True
            self.fields["currency"].read_only = True

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Currency must be a 3-letter alphabetic code.")
        return value

    def validate_current_price(self, value):
        if Decimal(value) < Decimal("0"):
            raise serializers.ValidationError("Price cannot be negative.")
        return value


class ChangeVehiclePriceSerializer(serializers.Serializer):
    new_price = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"))
    currency = serializers.CharField(max_length=3, required=False)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Currency must be a 3-letter alphabetic code.")
        return value
