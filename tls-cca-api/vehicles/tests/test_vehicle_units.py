"""Physical vehicle unit business rules."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from vehicles.models import VehicleBrand, VehicleCategory, VehicleModel, VehicleVariant, VehicleUnit
from vehicles.services.vehicle_services import create_vehicle_unit


def _variant():
    brand = VehicleBrand.objects.create(code="TOYOTA", name="Toyota")
    category = VehicleCategory.objects.create(code="PICKUP", name="Pick-up")
    model = VehicleModel.objects.create(brand=brand, category=category, code="HILUX", name="Hilux")
    return VehicleVariant.objects.create(model=model, code="DIESEL-28", name="2.8 D-4D 4x4")


@pytest.mark.django_db
class TestVehicleUnits:
    def test_stock_reference_is_generated_and_identifiers_are_unique(self, new_user):
        variant = _variant()
        first = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "vin": "VIN-0001",
                "chassis_number": "CH-0001",
                "color": "White",
                "current_price": Decimal("24000000.00"),
            },
        )
        assert first.stock_reference.startswith("VH-")
        assert first.stock_reference

        with pytest.raises(ValidationError):
            create_vehicle_unit(
                actor=new_user,
                validated_data={
                    "variant": variant,
                    "vin": "VIN-0001",
                    "chassis_number": "CH-0002",
                    "color": "Blue",
                    "current_price": Decimal("24500000.00"),
                },
            )

    def test_missing_color_is_persisted_as_empty_string(self, new_user):
        """A missing color must respect the non-nullable database column."""
        variant = _variant()
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "current_price": Decimal("1000.00"),
            },
        )

        assert vehicle.color == ""
        assert VehicleUnit.objects.get(pk=vehicle.pk).color == ""

    def test_clearing_color_uses_empty_string(self, new_user):
        from vehicles.services.vehicle_services import update_vehicle_unit

        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": _variant(),
                "color": "White",
                "current_price": Decimal("1000.00"),
            },
        )

        updated = update_vehicle_unit(
            vehicle=vehicle,
            actor=new_user,
            validated_data={"color": None},
        )

        assert updated.color == ""
        assert VehicleUnit.objects.get(pk=vehicle.pk).color == ""

    def test_update_cannot_change_stock_controlled_fields(self, new_user):
        variant = _variant()
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "current_price": Decimal("1000.00"),
            },
        )
        with pytest.raises(ValidationError):
            from vehicles.services.vehicle_services import update_vehicle_unit

            update_vehicle_unit(
                vehicle=vehicle,
                actor=new_user,
                validated_data={"status": VehicleUnit.STATUS_SOLD},
            )
