"""Vehicle current pricing and append-only history."""

from decimal import Decimal

import pytest

from vehicles.models import VehicleBrand, VehicleModel, VehicleVariant, VehiclePriceHistory
from vehicles.services.vehicle_services import change_vehicle_price, create_vehicle_unit


@pytest.mark.django_db
class TestVehiclePricing:
    def test_price_change_creates_before_after_history(self, new_user):
        brand = VehicleBrand.objects.create(code="NISSAN", name="Nissan")
        model = VehicleModel.objects.create(brand=brand, code="NAVARA", name="Navara")
        variant = VehicleVariant.objects.create(model=model, code="2.3D", name="2.3 dCi")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "current_price": Decimal("20000000.00"),
                "currency": "XAF",
            },
        )

        updated = change_vehicle_price(
            vehicle=vehicle,
            actor=new_user,
            new_price=Decimal("19500000.00"),
            reason="Commercial campaign",
        )
        assert updated.current_price == Decimal("19500000.00")
        assert VehiclePriceHistory.objects.filter(vehicle=vehicle).count() == 2
        latest = VehiclePriceHistory.objects.filter(vehicle=vehicle).first()
        assert latest.old_price == Decimal("20000000.00")
        assert latest.new_price == Decimal("19500000.00")

    def test_price_history_is_append_only(self, new_user):
        brand = VehicleBrand.objects.create(code="KIA", name="Kia")
        model = VehicleModel.objects.create(brand=brand, code="SPORTAGE", name="Sportage")
        variant = VehicleVariant.objects.create(model=model, code="LX", name="LX")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={"variant": variant, "current_price": Decimal("100.00")},
        )
        entry = VehiclePriceHistory.objects.filter(vehicle=vehicle).first()
        with pytest.raises(RuntimeError):
            entry.save()
