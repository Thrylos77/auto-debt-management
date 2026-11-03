"""Catalogue model and serializer contracts."""

import pytest
from django.core.exceptions import ValidationError

from vehicles.models import VehicleBrand, VehicleCategory, VehicleModel, VehicleVariant
from vehicles.serializers import VehicleCategorySerializer


@pytest.mark.django_db
class TestVehicleCatalogue:
    def test_catalogue_hierarchy_is_separated_from_physical_units(self):
        category = VehicleCategory.objects.create(code="PICKUP", name="Pick-up")
        brand = VehicleBrand.objects.create(code="TOYOTA", name="Toyota")
        model = VehicleModel.objects.create(
            brand=brand,
            category=category,
            code="HILUX",
            name="Hilux",
        )
        variant = VehicleVariant.objects.create(
            model=model,
            code="2.8-4X4",
            name="2.8 D-4D 4x4",
            fuel_type=VehicleVariant.FUEL_DIESEL,
            transmission=VehicleVariant.TRANSMISSION_AUTOMATIC,
        )

        assert variant.model.brand == brand
        assert variant.model.category == category
        assert not hasattr(variant, "color")

    def test_category_cycle_is_rejected_by_serializer_validation(self):
        parent = VehicleCategory.objects.create(code="SUV", name="SUV")
        child = VehicleCategory.objects.create(
            code="LUXURY-SUV",
            name="Luxury SUV",
            parent=parent,
        )

        serializer = VehicleCategorySerializer(
            child,
            data={"parent": child.pk},
            partial=True,
        )
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_category_model_rejects_self_parent_when_validated(self):
        category = VehicleCategory(code="TEST", name="Test")
        category.parent = category
        with pytest.raises(ValidationError):
            category.full_clean()
