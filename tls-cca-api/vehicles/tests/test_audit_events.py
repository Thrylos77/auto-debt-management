"""Vehicle-domain audit integration tests."""

from decimal import Decimal

import pytest

from audit.models import AuditEvent
from vehicles.models import (
    StockLocation,
    VehicleBrand,
    VehicleModel,
    VehicleUnit,
    VehicleVariant,
)
from vehicles.services import (
    change_vehicle_price,
    change_vehicle_status,
    create_vehicle_unit,
    receive_vehicle,
    release_reservation,
    reserve_vehicle,
    transfer_vehicle,
)


@pytest.mark.django_db
class TestVehicleAuditEvents:
    def test_vehicle_price_and_transfer_events_are_audited(self, new_user):
        location_a = StockLocation.objects.create(code="AUDIT-A", name="Audit A", type=StockLocation.TYPE_YARD)
        location_b = StockLocation.objects.create(code="AUDIT-B", name="Audit B", type=StockLocation.TYPE_YARD)
        brand = VehicleBrand.objects.create(code="VOLVO", name="Volvo")
        model = VehicleModel.objects.create(brand=brand, code="XC60", name="XC60")
        variant = VehicleVariant.objects.create(model=model, code="B5", name="B5")
        vehicle = create_vehicle_unit(actor=new_user, validated_data={"variant": variant, "current_price": Decimal("1000")})
        receive_vehicle(vehicle=vehicle, location=location_a, actor=new_user)
        transfer_vehicle(vehicle=vehicle, to_location=location_b, actor=new_user, reason="Audit transfer")
        change_vehicle_price(vehicle=vehicle, actor=new_user, new_price=Decimal("1100"), reason="Audit price")

        assert AuditEvent.objects.filter(action="vehicle.created", resource_id=str(vehicle.pk)).exists()
        assert AuditEvent.objects.filter(action="vehicle.received", resource_id=str(vehicle.pk)).exists()
        assert AuditEvent.objects.filter(action="vehicle.transferred", resource_id=str(vehicle.pk)).exists()
        price_event = AuditEvent.objects.filter(action="vehicle.price_changed", resource_id=str(vehicle.pk)).first()
        assert price_event is not None
        assert price_event.metadata["old_price"] == "1000"
        assert price_event.metadata["new_price"] == "1100"


@pytest.mark.django_db
class TestVehicleStatusAuditEvents:
    def test_reservation_and_release_emit_common_status_events(self, new_user, new_customer):
        location = StockLocation.objects.create(
            code="AUDIT-R",
            name="Audit Reservation",
            type=StockLocation.TYPE_YARD,
        )
        brand = VehicleBrand.objects.create(code="HONDA", name="Honda")
        model = VehicleModel.objects.create(brand=brand, code="CRV", name="CR-V")
        variant = VehicleVariant.objects.create(model=model, code="EX", name="EX")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={"variant": variant, "current_price": Decimal("1000")},
        )
        receive_vehicle(vehicle=vehicle, location=location, actor=new_user)

        reservation = reserve_vehicle(
            vehicle=vehicle,
            customer=new_customer,
            actor=new_user,
        )
        release_reservation(reservation=reservation, actor=new_user, reason="Audit release")

        events = list(
            AuditEvent.objects.filter(
                action="vehicle.status_changed",
                resource_id=str(vehicle.pk),
            ).values_list("metadata", flat=True)
        )
        assert any(event["previous_status"] == "IN_STOCK" and event["new_status"] == "RESERVED" for event in events)
        assert any(event["previous_status"] == "RESERVED" and event["new_status"] == "IN_STOCK" for event in events)

    def test_return_emits_vehicle_returned_once(self, new_user):
        brand = VehicleBrand.objects.create(code="MAZDA", name="Mazda")
        model = VehicleModel.objects.create(brand=brand, code="CX5", name="CX-5")
        variant = VehicleVariant.objects.create(model=model, code="G2", name="G2")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={"variant": variant, "current_price": Decimal("1000")},
        )
        vehicle.status = VehicleUnit.STATUS_SOLD
        vehicle.save(update_fields=["status", "updated_at"])

        change_vehicle_status(
            vehicle=vehicle,
            new_status=VehicleUnit.STATUS_RETURNED,
            actor=new_user,
            reason="Customer return",
        )

        assert AuditEvent.objects.filter(
            action="vehicle.returned",
            resource_id=str(vehicle.pk),
        ).count() == 1
