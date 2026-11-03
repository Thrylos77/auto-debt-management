"""QR-code privacy contract."""

from decimal import Decimal

import pytest

from vehicles.models import VehicleBrand, VehicleModel, VehicleVariant
from vehicles.services import build_vehicle_qr_code, create_vehicle_unit


@pytest.mark.django_db
class TestVehicleQrCode:
    def test_qr_payload_uses_only_stock_reference(self, new_user, monkeypatch):
        brand = VehicleBrand.objects.create(code="BMW", name="BMW")
        model = VehicleModel.objects.create(brand=brand, code="X3", name="X3")
        variant = VehicleVariant.objects.create(model=model, code="30I", name="xDrive30i")
        vehicle = create_vehicle_unit(
            actor=new_user,
            validated_data={
                "variant": variant,
                "vin": "SECRET-VIN-123",
                "acquisition_cost": Decimal("123456.00"),
                "current_price": Decimal("456789.00"),
            },
        )
        captured = {}
        from vehicles.services import vehicle_services

        original_add_data = vehicle_services.qrcode.QRCode.add_data

        def capture(self, data, *args, **kwargs):
            captured["data"] = data
            return original_add_data(self, data, *args, **kwargs)

        monkeypatch.setattr(vehicle_services.qrcode.QRCode, "add_data", capture)
        payload = build_vehicle_qr_code(vehicle)
        assert payload.startswith(b"\x89PNG")
        assert captured["data"] == vehicle.stock_reference
