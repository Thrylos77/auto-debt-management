"""V07 vehicle-domain notification integration tests."""

from decimal import Decimal

import pytest

from notifications.models import Notification
from vehicles.models import VehicleBrand, VehicleModel, VehicleVariant
from vehicles.services import create_vehicle_unit, receive_vehicle, reserve_vehicle
from vehicles.models import StockLocation


@pytest.mark.django_db
class TestVehicleNotifications:
    def test_reservation_creates_an_idempotent_business_notification(self, new_user, new_customer):
        location = StockLocation.objects.create(
            code="NOTIF-YARD",
            name="Notification Yard",
            type=StockLocation.TYPE_YARD,
        )
        brand = VehicleBrand.objects.create(code="TOYOTA-N", name="Toyota")
        model = VehicleModel.objects.create(brand=brand, code="RAV4-N", name="RAV4")
        variant = VehicleVariant.objects.create(model=model, code="HYB", name="Hybrid")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "current_price": Decimal("1000"),
            },
        )
        receive_vehicle(vehicle=vehicle, location=location, actor=new_user)

        reservation = reserve_vehicle(
            vehicle=vehicle,
            customer=new_customer,
            actor=new_user,
        )

        notification = Notification.objects.get(
            user=new_user,
            idempotency_key=f"vehicle-reservation-created:{reservation.pk}",
        )
        assert notification.category == Notification.BUSINESS
        assert notification.resource_id == str(reservation.pk)
        assert notification.data["vehicle_id"] == vehicle.pk
