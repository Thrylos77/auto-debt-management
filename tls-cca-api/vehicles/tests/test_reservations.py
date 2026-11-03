"""Reservation lifecycle and concurrency guards."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from vehicles.models import StockLocation, VehicleBrand, VehicleModel, VehicleVariant, VehicleUnit, VehicleReservation
from vehicles.services import create_vehicle_unit, receive_vehicle, release_reservation, reserve_vehicle


def _vehicle(user, location):
    brand = VehicleBrand.objects.create(code="HYUNDAI", name="Hyundai")
    model = VehicleModel.objects.create(brand=brand, code="TUCSON", name="Tucson")
    variant = VehicleVariant.objects.create(model=model, code="GL", name="GL")
    vehicle = create_vehicle_unit(actor=user, validated_data={"variant": variant, "current_price": Decimal("1000")})
    receive_vehicle(vehicle=vehicle, location=location, actor=user)
    return vehicle


@pytest.mark.django_db
class TestReservations:
    def test_only_one_active_reservation_can_exist(self, new_user, new_customer):
        location = StockLocation.objects.create(code="YARD-R", name="Yard Reservations", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user, location)
        first = reserve_vehicle(vehicle=vehicle, customer=new_customer, actor=new_user)
        assert first.status == VehicleReservation.ACTIVE
        with pytest.raises(ValidationError):
            reserve_vehicle(
                vehicle=vehicle,
                customer=new_customer,
                actor=new_user,
                expires_at=timezone.now() + timedelta(days=1),
            )
        assert VehicleReservation.objects.filter(vehicle=vehicle, status=VehicleReservation.ACTIVE).count() == 1

    def test_release_returns_vehicle_to_stock(self, new_user, new_customer):
        location = StockLocation.objects.create(code="YARD-R2", name="Yard R2", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user, location)
        reservation = reserve_vehicle(vehicle=vehicle, customer=new_customer, actor=new_user)
        release_reservation(reservation=reservation, actor=new_user, reason="Customer changed plan")
        vehicle.refresh_from_db()
        reservation.refresh_from_db()
        assert vehicle.status == VehicleUnit.STATUS_IN_STOCK
        assert reservation.status == VehicleReservation.RELEASED

    def test_blocked_vehicle_cannot_be_reserved(self, new_user, new_customer):
        location = StockLocation.objects.create(code="YARD-R3", name="Yard R3", type=StockLocation.TYPE_YARD)
        vehicle = _vehicle(new_user, location)
        vehicle.status = VehicleUnit.STATUS_BLOCKED
        vehicle.save()
        with pytest.raises(PermissionError):
            reserve_vehicle(vehicle=vehicle, customer=new_customer, actor=new_user)
