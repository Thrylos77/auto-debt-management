"""Serializers for the automotive catalogue hierarchy."""

from rest_framework import serializers

from vehicles.models import VehicleBrand, VehicleCategory, VehicleModel, VehicleVariant


class VehicleCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = VehicleCategory
        fields = (
            "id",
            "code",
            "name",
            "parent",
            "parent_name",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "parent_name", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance or VehicleCategory()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        try:
            instance.full_clean()
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ("id", "code", "name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance or VehicleBrand()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        try:
            instance.full_clean()
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class VehicleModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = VehicleModel
        fields = (
            "id",
            "brand",
            "brand_name",
            "category",
            "category_name",
            "code",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "brand_name", "category_name", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance or VehicleModel()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        try:
            instance.full_clean()
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class VehicleVariantSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source="model.name", read_only=True)
    brand_name = serializers.CharField(source="model.brand.name", read_only=True)

    class Meta:
        model = VehicleVariant
        fields = (
            "id",
            "model",
            "model_name",
            "brand_name",
            "code",
            "name",
            "engine_description",
            "fuel_type",
            "transmission",
            "seats",
            "power_value",
            "power_unit",
            "technical_specs",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "model_name", "brand_name", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance or VehicleVariant()
        for field_name, value in attrs.items():
            setattr(instance, field_name, value)
        try:
            instance.full_clean()
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc
        return attrs
