"""Stock receipt, transfer and explicit adjustment tests."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from vehicles.models import StockLocation, StockMovement, VehicleBrand, VehicleModel, VehicleVariant
from vehicles.services import create_vehicle_unit, receive_vehicle, transfer_vehicle


def _vehicle(user):
    brand = VehicleBrand.objects.create(code="ISUZU", name="Isuzu")
    model = VehicleModel.objects.create(brand=brand, code="D-MAX", name="D-Max")
    variant = VehicleVariant.objects.create(model=model, code="30D", name="3.0 Diesel")
    return create_vehicle_unit(actor=user, validated_data={"variant": variant, "current_price": Decimal("1000")})


@pytest.mark.django_db
class TestStockServices:
    def test_receive_and_transfer_are_atomic_and_journaled(self, new_user):
        location_a = StockLocation.objects.create(code="YARD-A", name="Yard A", type=StockLocation.TYPE_YARD)
        location_b = StockLocation.objects.create(code="SHOWROOM", name="Showroom", type=StockLocation.TYPE_SHOWROOM)
        vehicle = _vehicle(new_user)

        receive_vehicle(vehicle=vehicle, location=location_a, actor=new_user)
        vehicle.refresh_from_db()
        assert vehicle.current_location_id == location_a.pk
        assert StockMovement.objects.filter(vehicle=vehicle, movement_type=StockMovement.RECEIVED).count() == 1

        transfer_vehicle(vehicle=vehicle, to_location=location_b, actor=new_user, reason="Display rotation")
        vehicle.refresh_from_db()
        assert vehicle.current_location_id == location_b.pk
        movement = StockMovement.objects.filter(vehicle=vehicle, movement_type=StockMovement.TRANSFERRED).first()
        assert movement.from_location_id == location_a.pk
        assert movement.to_location_id == location_b.pk

    def test_transfer_requires_in_stock_status(self, new_user):
        location = StockLocation.objects.create(code="YARD-X", name="Yard X", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user)
        vehicle.status = "BLOCKED"
        vehicle.save()
        with pytest.raises(ValidationError):
            transfer_vehicle(vehicle=vehicle, to_location=location, actor=new_user)
