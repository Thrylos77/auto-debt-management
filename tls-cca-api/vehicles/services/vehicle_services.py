"""Application services for physical vehicle units."""

from io import BytesIO
from decimal import Decimal
from datetime import date

import qrcode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from audit.services import AuditService
from core.events import (
    vehicle_created,
    vehicle_image_added,
    vehicle_price_changed,
    vehicle_status_changed,
    vehicle_updated,
)
from configuration.services import ConfigurationService

from vehicles.models import VehicleImage, VehiclePriceHistory, VehicleUnit
from vehicles.policies import VehiclePolicy

IMAGE_MAX_SIZE_KEY = "vehicles.image.max_size_bytes"
DEFAULT_IMAGE_MAX_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

STATUS_TRANSITIONS = {
    VehicleUnit.STATUS_IN_STOCK: {
        VehicleUnit.STATUS_RESERVED,
        VehicleUnit.STATUS_SOLD,
        VehicleUnit.STATUS_BLOCKED,
        VehicleUnit.STATUS_ARCHIVED,
    },
    VehicleUnit.STATUS_RESERVED: {
        VehicleUnit.STATUS_IN_STOCK,
        VehicleUnit.STATUS_SOLD,
        VehicleUnit.STATUS_BLOCKED,
    },
    VehicleUnit.STATUS_SOLD: {
        VehicleUnit.STATUS_DELIVERED,
        VehicleUnit.STATUS_RETURNED,
    },
    VehicleUnit.STATUS_DELIVERED: {
        VehicleUnit.STATUS_RETURNED,
        VehicleUnit.STATUS_ARCHIVED,
    },
    VehicleUnit.STATUS_BLOCKED: {
        VehicleUnit.STATUS_IN_STOCK,
    },
    VehicleUnit.STATUS_RETURNED: {
        VehicleUnit.STATUS_IN_STOCK,
        VehicleUnit.STATUS_BLOCKED,
        VehicleUnit.STATUS_ARCHIVED,
    },
    VehicleUnit.STATUS_ARCHIVED: set(),
}

MOVEMENT_FOR_STATUS = {
    VehicleUnit.STATUS_SOLD: "SOLD",
    VehicleUnit.STATUS_DELIVERED: "DELIVERED",
    VehicleUnit.STATUS_RETURNED: "RETURNED",
    VehicleUnit.STATUS_BLOCKED: "BLOCKED",
    VehicleUnit.STATUS_IN_STOCK: "UNBLOCKED",
}


def _normalize_optional_identifier(value):
    """Normalize nullable identifiers to None when no value is supplied."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _normalize_optional_text(value):
    """Normalize optional, non-nullable text fields to an empty string."""
    if value is None:
        return ""
    return str(value).strip()


def create_vehicle_unit(*, actor, validated_data, request=None):
    """Create one physical vehicle and its initial price history record."""
    if not VehiclePolicy.can_create(actor):
        raise PermissionError("You do not have permission to create vehicles.")

    data = dict(validated_data)
    data["currency"] = str(data.get("currency", "XAF")).strip().upper()
    for field_name in (
        "vin",
        "chassis_number",
        "engine_number",
        "registration_number",
    ):
        data[field_name] = _normalize_optional_identifier(data.get(field_name))
    data["color"] = _normalize_optional_text(data.get("color"))

    vehicle = VehicleUnit(**data)
    vehicle.full_clean()
    with transaction.atomic():
        vehicle.save(force_insert=True)
        VehiclePriceHistory.objects.create(
            vehicle=vehicle,
            old_price=None,
            new_price=vehicle.current_price,
            currency=vehicle.currency,
            reason="Initial vehicle price",
            changed_by=actor if getattr(actor, "pk", None) else None,
        )
        vehicle_created.send(
            sender=VehicleUnit,
            vehicle=vehicle,
            actor=actor,
            request=request,
        )
    return vehicle


def update_vehicle_unit(*, vehicle, actor, validated_data, request=None):
    """Update non-stock-control vehicle attributes through a whitelist."""
    if not VehiclePolicy.can_update(actor, vehicle):
        raise PermissionError("You do not have permission to update this vehicle.")

    forbidden = {"stock_reference", "status", "current_location", "current_price", "currency"}
    if forbidden.intersection(validated_data):
        raise ValidationError("Stock-controlled fields must be changed through dedicated services.")

    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        for field_name, value in validated_data.items():
            if field_name in {
                "vin",
                "chassis_number",
                "engine_number",
                "registration_number",
            }:
                value = _normalize_optional_identifier(value)
            elif field_name == "color":
                value = _normalize_optional_text(value)
            setattr(locked, field_name, value)
        locked.full_clean()
        locked.save()
        vehicle_updated.send(
            sender=VehicleUnit,
            vehicle=locked,
            actor=actor,
            request=request,
        )
    return locked


def change_vehicle_status(
    *,
    vehicle,
    new_status,
    actor,
    reason="",
    reference_type="",
    reference_id="",
    movement_type=None,
    request=None,
):
    """Atomically change operational status and append a stock movement."""
    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        if not VehiclePolicy.can_change_status(actor, locked):
            raise PermissionError("You do not have permission to change vehicle status.")
        if new_status not in dict(VehicleUnit.STATUS_CHOICES):
            raise ValidationError({"status": "Unsupported vehicle status."})
        if locked.status == new_status:
            raise ValidationError({"status": "Vehicle is already in the requested status."})
        if new_status not in STATUS_TRANSITIONS.get(locked.status, set()):
            raise ValidationError(
                {"status": f"Transition {locked.status} → {new_status} is not allowed."}
            )
        if new_status == VehicleUnit.STATUS_RESERVED:
            from vehicles.models import VehicleReservation

            if not VehicleReservation.objects.filter(
                vehicle=locked,
                status=VehicleReservation.ACTIVE,
            ).exists():
                raise ValidationError("A reservation is required before a vehicle can become reserved.")
        if new_status == VehicleUnit.STATUS_SOLD:
            from vehicles.models import VehicleReservation

            if VehicleReservation.objects.filter(
                vehicle=locked,
                status=VehicleReservation.ACTIVE,
            ).exists():
                raise ValidationError("An active reservation must be converted or released before sale.")

        previous_status = locked.status
        locked.status = new_status
        locked.full_clean()
        locked.save(update_fields=["status", "updated_at"])

        from vehicles.models import StockMovement

        StockMovement.objects.create(
            vehicle=locked,
            movement_type=movement_type or MOVEMENT_FOR_STATUS.get(new_status, "ADJUSTED"),
            from_location=locked.current_location,
            to_location=locked.current_location,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            performed_by=actor if getattr(actor, "pk", None) else None,
        )
        vehicle_status_changed.send(
            sender=VehicleUnit,
            vehicle=locked,
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            request=request,
        )
        if new_status == VehicleUnit.STATUS_DELIVERED:
            from core.events import vehicle_delivered

            vehicle_delivered.send(
                sender=VehicleUnit,
                vehicle=locked,
                actor=actor,
                request=request,
            )
        if new_status == VehicleUnit.STATUS_RETURNED:
            from core.events import vehicle_returned

            vehicle_returned.send(
                sender=VehicleUnit,
                vehicle=locked,
                actor=actor,
                request=request,
            )
        return locked


def change_vehicle_price(
    *,
    vehicle,
    new_price,
    actor,
    reason="",
    currency=None,
    request=None,
):
    """Change the current price while preserving a before/after history row."""
    if not VehiclePolicy.can_change_price(actor, vehicle):
        raise PermissionError("You do not have permission to change vehicle price.")

    new_price = Decimal(str(new_price))
    if new_price < 0:
        raise ValidationError({"new_price": "Price cannot be negative."})

    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        effective_currency = (currency or locked.currency).strip().upper()
        if len(effective_currency) != 3:
            raise ValidationError({"currency": "Currency must be a 3-letter code."})
        if locked.current_price == new_price and locked.currency == effective_currency:
            raise ValidationError("The price and currency are unchanged.")

        old_price = locked.current_price
        old_currency = locked.currency
        locked.current_price = new_price
        locked.currency = effective_currency
        locked.full_clean()
        locked.save(update_fields=["current_price", "currency", "updated_at"])
        VehiclePriceHistory.objects.create(
            vehicle=locked,
            old_price=old_price,
            new_price=new_price,
            currency=effective_currency,
            reason=reason,
            changed_by=actor if getattr(actor, "pk", None) else None,
        )
        vehicle_price_changed.send(
            sender=VehicleUnit,
            vehicle=locked,
            actor=actor,
            old_price=old_price,
            new_price=new_price,
            old_currency=old_currency,
            new_currency=effective_currency,
            reason=reason,
            request=request,
        )
    return locked


def _max_image_size() -> int:
    return int(
        ConfigurationService.get(
            IMAGE_MAX_SIZE_KEY,
            default=getattr(settings, "VEHICLE_IMAGE_MAX_SIZE_BYTES", DEFAULT_IMAGE_MAX_SIZE),
        )
    )


def _inspect_image(file_obj):
    max_size = _max_image_size()
    size = getattr(file_obj, "size", None)
    if size is None:
        payload = file_obj.read()
        size = len(payload)
        file_obj.seek(0)
    if size > max_size:
        raise ValidationError({"file": f"Image exceeds the maximum size of {max_size} bytes."})

    content = file_obj.read()
    file_obj.seek(0)
    if len(content) > max_size:
        raise ValidationError({"file": f"Image exceeds the maximum size of {max_size} bytes."})

    try:
        image = Image.open(BytesIO(content))
        image.verify()
        detected_format = image.format
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError({"file": "The uploaded file is not a valid image."}) from exc

    mime_type = ALLOWED_IMAGE_MIME_TYPES.get(detected_format)
    if not mime_type:
        raise ValidationError({"file": "Only JPEG, PNG and WebP images are allowed."})

    checksum = VehicleImage.checksum_for(content)
    return content, size, mime_type, checksum


def add_vehicle_image(*, vehicle, actor, file_obj, is_primary=False, sort_order=0, caption="", request=None):
    """Validate and persist one image without storing its binary data in audit metadata."""
    if not VehiclePolicy.can_manage_images(actor, vehicle):
        raise PermissionError("You do not have permission to manage vehicle images.")
    if file_obj is None:
        raise ValidationError({"file": "An image file is required."})

    content, size, mime_type, checksum = _inspect_image(file_obj)
    file_obj.seek(0)

    with transaction.atomic():
        locked_vehicle = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        if is_primary:
            VehicleImage.objects.filter(vehicle=locked_vehicle, is_primary=True).update(is_primary=False)

        image = VehicleImage(
            vehicle=locked_vehicle,
            file=file_obj,
            is_primary=is_primary,
            sort_order=sort_order,
            caption=(caption or "").strip(),
            mime_type=mime_type,
            file_size=size,
            checksum=checksum,
            uploaded_by=actor if getattr(actor, "pk", None) else None,
        )
        image.full_clean(exclude=["file"])
        image.save()
        vehicle_image_added.send(
            sender=VehicleImage,
            image=image,
            vehicle=locked_vehicle,
            actor=actor,
            request=request,
        )
    return image


def build_vehicle_qr_code(vehicle) -> bytes:
    """Build a PNG QR code containing only the non-sensitive stock reference."""
    payload = vehicle.stock_reference
    qr = qrcode.QRCode(version=None, box_size=8, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image()
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_vehicle_qr(*, vehicle, actor):
    """Authorize and generate the vehicle QR payload."""
    if not VehiclePolicy.can_generate_qr(actor, vehicle):
        raise PermissionError("You do not have permission to generate vehicle QR codes.")
    return build_vehicle_qr_code(vehicle)
