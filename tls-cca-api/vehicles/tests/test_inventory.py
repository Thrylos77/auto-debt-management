"""Physical inventory snapshot and explicit adjustment tests."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from vehicles.models import InventoryItem, InventorySession, StockLocation, VehicleBrand, VehicleModel, VehicleVariant, VehicleUnit
from vehicles.services import (
    create_adjustment_from_inventory,
    create_inventory_session,
    create_vehicle_unit,
    record_inventory_item,
    receive_vehicle,
    start_inventory,
    submit_inventory,
    validate_inventory,
)


def _vehicle(user, location, code="V1"):
    brand = VehicleBrand.objects.get_or_create(code=f"BR-{code}", defaults={"name": f"Brand {code}"})[0]
    model = VehicleModel.objects.create(brand=brand, code=f"MOD-{code}", name=f"Model {code}")
    variant = VehicleVariant.objects.create(model=model, code=f"VAR-{code}", name=f"Variant {code}")
    vehicle = create_vehicle_unit(actor=user, validated_data={"variant": variant, "current_price": Decimal("1000")})
    receive_vehicle(vehicle=vehicle, location=location, actor=user)
    return vehicle


@pytest.mark.django_db
class TestInventory:
    def test_start_snapshots_expected_vehicles_and_validate_does_not_change_stock(self, new_user):
        location = StockLocation.objects.create(code="INV-YARD", name="Inventory Yard", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user, location)
        session = create_inventory_session(location=location, actor=new_user)
        start_inventory(session=session, actor=new_user)
        item = InventoryItem.objects.get(session=session, vehicle=vehicle)
        assert item.expected_location_id == location.pk
        assert item.found is False

        record_inventory_item(
            session=session,
            actor=new_user,
            vehicle=vehicle,
            observed_location=location,
            observed_status=vehicle.status,
        )
        submit_inventory(session=session, actor=new_user)
        session = validate_inventory(session=session, actor=new_user)
        vehicle.refresh_from_db()
        assert vehicle.current_location_id == location.pk
        assert vehicle.status == VehicleUnit.STATUS_IN_STOCK
        assert session.status == InventorySession.VALIDATED

    def test_adjustment_is_explicit_and_auditable(self, new_user):
        location_a = StockLocation.objects.create(code="INV-A", name="Inventory A", type=StockLocation.TYPE_YARD)
        location_b = StockLocation.objects.create(code="INV-B", name="Inventory B", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user, location_a, code="V2")
        session = create_inventory_session(location=location_b, actor=new_user)
        start_inventory(session=session, actor=new_user)
        record_inventory_item(
            session=session,
            actor=new_user,
            vehicle=vehicle,
            observed_location=location_b,
            observed_status=vehicle.status,
        )
        submit_inventory(session=session, actor=new_user)
        validate_inventory(session=session, actor=new_user)
        item = InventoryItem.objects.get(session=session, vehicle=vehicle)
        assert item.result == InventoryItem.RESULT_UNEXPECTED
        create_adjustment_from_inventory(
            item=item,
            actor=new_user,
            reason="Physical count confirms vehicle is at this location.",
        )
        vehicle.refresh_from_db()
        assert vehicle.current_location_id == location_b.pk

        with pytest.raises(ValidationError):
            create_adjustment_from_inventory(item=item, actor=new_user, reason="Duplicate correction")
