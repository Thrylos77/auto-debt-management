"""Serializer mass-assignment and write-whitelist tests."""

from decimal import Decimal

import pytest

from vehicles.models import StockLocation, VehicleBrand, VehicleModel, VehicleVariant, VehicleUnit
from vehicles.serializers import VehicleUnitSerializer
from vehicles.services import create_vehicle_unit


@pytest.mark.django_db
class TestVehicleSerializerSecurity:
    def test_status_location_and_stock_reference_are_read_only(self, new_user):
        brand = VehicleBrand.objects.create(code="MERCEDES", name="Mercedes")
        model = VehicleModel.objects.create(brand=brand, code="GLC", name="GLC")
        variant = VehicleVariant.objects.create(model=model, code="220D", name="220 d")
        location = StockLocation.objects.create(code="SEC-YARD", name="Security Yard", type=StockLocation.TYPE_YARD)
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={"variant": variant, "current_price": Decimal("1000")},
        )
        serializer = VehicleUnitSerializer(
            vehicle,
            data={
                "status": VehicleUnit.STATUS_SOLD,
                "current_location": location.pk,
                "stock_reference": "ATTACK",
                "current_price": "9999999.00",
                "color": "Black",
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data
        assert "current_location" not in serializer.validated_data
        assert "stock_reference" not in serializer.validated_data
        assert "current_price" not in serializer.validated_data
        assert serializer.validated_data["color"] == "Black"
