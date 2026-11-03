"""Vehicle image validation and primary-image rules."""

from io import BytesIO
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from vehicles.models import VehicleBrand, VehicleModel, VehicleVariant, VehicleUnit, VehicleImage
from vehicles.services.vehicle_services import add_vehicle_image, create_vehicle_unit


def _vehicle(user):
    brand = VehicleBrand.objects.create(code="FORD", name="Ford")
    model = VehicleModel.objects.create(brand=brand, code="RANGER", name="Ranger")
    variant = VehicleVariant.objects.create(model=model, code="XLT", name="XLT")
    return create_vehicle_unit(
        actor=user,
        validated_data={"variant": variant, "current_price": Decimal("1000.00")},
    )


def _png_file(name="vehicle.png"):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.mark.django_db
class TestVehicleImages:
    def test_only_supported_real_images_are_accepted(self, new_user):
        vehicle = _vehicle(new_user)
        image = add_vehicle_image(
            vehicle=vehicle,
            actor=new_user,
            file_obj=_png_file(),
            is_primary=True,
        )
        assert image.mime_type == "image/png"
        assert image.file_size > 0
        assert len(image.checksum) == 64

        pdf = SimpleUploadedFile(
            "vehicle.pdf",
            b"%PDF-1.7\nnot-an-image",
            content_type="application/pdf",
        )
        with pytest.raises(Exception):
            add_vehicle_image(vehicle=vehicle, actor=new_user, file_obj=pdf)

    def test_new_primary_image_demotes_previous_primary(self, new_user):
        vehicle = _vehicle(new_user)
        first = add_vehicle_image(
            vehicle=vehicle,
            actor=new_user,
            file_obj=_png_file("one.png"),
            is_primary=True,
        )
        second = add_vehicle_image(
            vehicle=vehicle,
            actor=new_user,
            file_obj=_png_file("two.png"),
            is_primary=True,
        )
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.is_primary is False
        assert second.is_primary is True
        assert VehicleImage.objects.filter(vehicle=vehicle, is_primary=True).count() == 1
