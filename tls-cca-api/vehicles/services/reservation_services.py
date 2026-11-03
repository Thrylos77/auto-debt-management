"""Atomic vehicle reservation services."""

from datetime import timedelta
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from configuration.services import ConfigurationService
from core.events import (
    vehicle_reservation_expired,
    vehicle_reservation_released,
    vehicle_reserved,
    vehicle_status_changed,
)

from vehicles.models import StockMovement, VehicleReservation, VehicleUnit
from vehicles.policies import ReservationPolicy

DEFAULT_RESERVATION_DURATION_KEY = "vehicles.reservation.default_duration_hours"
DEFAULT_RESERVATION_DURATION_HOURS = 72


def generate_reservation_reference() -> str:
    return f"RSV-{uuid.uuid4().hex[:12].upper()}"


def _default_duration_hours() -> int:
    return int(
        ConfigurationService.get(
            DEFAULT_RESERVATION_DURATION_KEY,
            default=DEFAULT_RESERVATION_DURATION_HOURS,
        )
    )


def reserve_vehicle(
    *,
    vehicle,
    customer,
    actor,
    expires_at=None,
    reason="",
    request=None,
):
    """Create one active reservation under a row lock on the vehicle."""
    with transaction.atomic():
        locked_vehicle = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)

        due_reservations = list(
            VehicleReservation.objects.select_for_update().filter(
                vehicle=locked_vehicle,
                status=VehicleReservation.ACTIVE,
                expires_at__lte=timezone.now(),
            )
        )
        for reservation in due_reservations:
            _expire_locked_reservation(reservation, locked_vehicle, actor=actor, request=request)

        if not ReservationPolicy.can_create_for_actor(actor):
            raise PermissionError("You do not have permission to reserve this vehicle.")

        if VehicleReservation.objects.filter(
            vehicle=locked_vehicle,
            status=VehicleReservation.ACTIVE,
        ).exists():
            raise ValidationError("Vehicle already has an active reservation.")

        if not ReservationPolicy.can_create(actor, locked_vehicle, customer):
            raise PermissionError("This vehicle or customer is not eligible for reservation.")

        now = timezone.now()
        if expires_at is None:
            expires_at = now + timedelta(hours=_default_duration_hours())
        if expires_at <= now:
            raise ValidationError({"expires_at": "Reservation expiration must be in the future."})

        reservation = VehicleReservation(
            reference=generate_reservation_reference(),
            vehicle=locked_vehicle,
            customer=customer,
            reserved_by=actor,
            status=VehicleReservation.ACTIVE,
            reserved_at=now,
            expires_at=expires_at,
        )
        reservation.full_clean()
        reservation.save(force_insert=True)

        previous_status = locked_vehicle.status
        locked_vehicle.status = VehicleUnit.STATUS_RESERVED
        locked_vehicle.full_clean()
        locked_vehicle.save(update_fields=["status", "updated_at"])

        StockMovement.objects.create(
            vehicle=locked_vehicle,
            movement_type=StockMovement.RESERVED,
            from_location=locked_vehicle.current_location,
            to_location=locked_vehicle.current_location,
            reference_type="vehicle_reservation",
            reference_id=str(reservation.pk),
            reason=reason,
            performed_by=actor,
            metadata={"previous_status": previous_status, "new_status": locked_vehicle.status},
        )
        vehicle_status_changed.send(
            sender=VehicleUnit,
            vehicle=locked_vehicle,
            actor=actor,
            previous_status=previous_status,
            new_status=locked_vehicle.status,
            reason=reason,
            request=request,
        )
        vehicle_reserved.send(
            sender=VehicleReservation,
            reservation=reservation,
            vehicle=locked_vehicle,
            actor=actor,
            request=request,
        )
        return reservation


def _release_locked_reservation(
    reservation,
    vehicle,
    *,
    status,
    actor,
    reason="",
    movement_type=StockMovement.RELEASED,
    request=None,
):
    if reservation.status != VehicleReservation.ACTIVE:
        raise ValidationError("Only active reservations can be released or expired.")

    now = timezone.now()
    reservation.status = status
    reservation.released_at = now
    reservation.released_by = actor if getattr(actor, "pk", None) else None
    reservation.release_reason = reason
    reservation.full_clean()
    reservation.save(update_fields=["status", "released_at", "released_by", "release_reason", "updated_at"])

    previous_status = vehicle.status
    vehicle.status = VehicleUnit.STATUS_IN_STOCK
    vehicle.full_clean()
    vehicle.save(update_fields=["status", "updated_at"])

    StockMovement.objects.create(
        vehicle=vehicle,
        movement_type=movement_type,
        from_location=vehicle.current_location,
        to_location=vehicle.current_location,
        reference_type="vehicle_reservation",
        reference_id=str(reservation.pk),
        reason=reason,
        performed_by=actor if getattr(actor, "pk", None) else None,
        metadata={
            "previous_status": previous_status,
            "new_status": vehicle.status,
            "reservation_status": status,
        },
    )
    vehicle_status_changed.send(
        sender=VehicleUnit,
        vehicle=vehicle,
        actor=actor,
        previous_status=previous_status,
        new_status=vehicle.status,
        reason=reason,
        request=request,
    )
    return reservation


def release_reservation(*, reservation, actor, reason="", request=None):
    """Release an active reservation and return the vehicle to stock."""
    with transaction.atomic():
        locked = VehicleReservation.objects.select_for_update().select_related("vehicle").get(pk=reservation.pk)
        if not ReservationPolicy.can_release(actor, locked):
            raise PermissionError("You do not have permission to release this reservation.")
        vehicle = VehicleUnit.objects.select_for_update().get(pk=locked.vehicle_id)
        released = _release_locked_reservation(
            locked,
            vehicle,
            status=VehicleReservation.RELEASED,
            actor=actor,
            reason=reason,
            movement_type=StockMovement.RELEASED,
            request=request,
        )
        vehicle_reservation_released.send(
            sender=VehicleReservation,
            reservation=released,
            vehicle=vehicle,
            actor=actor,
            request=request,
        )
        return released


def _expire_locked_reservation(reservation, vehicle, *, actor=None, request=None):
    expired = _release_locked_reservation(
        reservation,
        vehicle,
        status=VehicleReservation.EXPIRED,
        actor=actor,
        reason="Reservation expired.",
        movement_type=StockMovement.RELEASED,
        request=request,
    )
    vehicle_reservation_expired.send(
        sender=VehicleReservation,
        reservation=expired,
        vehicle=vehicle,
        actor=actor,
        request=request,
    )
    return expired


def expire_reservation(*, reservation, actor=None, request=None):
    """Expire one reservation only after its deadline has passed."""
    with transaction.atomic():
        locked = VehicleReservation.objects.select_for_update().select_related("vehicle").get(pk=reservation.pk)
        if not ReservationPolicy.can_expire(actor, locked):
            raise PermissionError("You do not have permission to expire reservations.")
        if locked.status != VehicleReservation.ACTIVE:
            raise ValidationError("Only active reservations can expire.")
        if locked.expires_at > timezone.now():
            raise ValidationError("Reservation has not reached its expiration time.")
        vehicle = VehicleUnit.objects.select_for_update().get(pk=locked.vehicle_id)
        return _expire_locked_reservation(locked, vehicle, actor=actor, request=request)


def expire_due_reservations(*, limit=None, actor=None, request=None) -> int:
    """Expire due reservations in small deterministic batches for maintenance jobs."""
    queryset = VehicleReservation.objects.filter(
        status=VehicleReservation.ACTIVE,
        expires_at__lte=timezone.now(),
    ).order_by("expires_at", "id")
    if limit:
        queryset = queryset[:limit]
    reservation_ids = list(queryset.values_list("id", flat=True))
    expired_count = 0
    for reservation_id in reservation_ids:
        try:
            expire_reservation(
                reservation=VehicleReservation(pk=reservation_id),
                actor=actor,
                request=request,
            )
        except ValidationError:
            continue
        expired_count += 1
    return expired_count


def convert_reservation_to_sale(*, reservation, sale_reference, actor, request=None):
    """Close a reservation as converted to a sale without a hard FK to V08."""
    if not sale_reference or not str(sale_reference).strip():
        raise ValidationError({"sale_reference": "Sale reference is required."})

    with transaction.atomic():
        locked = VehicleReservation.objects.select_for_update().get(pk=reservation.pk)
        if not ReservationPolicy.can_convert_to_sale(actor, locked):
            raise PermissionError("You do not have permission to convert this reservation.")
        vehicle = VehicleUnit.objects.select_for_update().get(pk=locked.vehicle_id)
        now = timezone.now()
        locked.status = VehicleReservation.CONVERTED_TO_SALE
        locked.released_at = now
        locked.released_by = actor if getattr(actor, "pk", None) else None
        locked.release_reason = f"Converted to sale {str(sale_reference).strip()}."
        locked.full_clean()
        locked.save(update_fields=["status", "released_at", "released_by", "release_reason", "updated_at"])

        if vehicle.status != VehicleUnit.STATUS_RESERVED:
            raise ValidationError("Reserved vehicle is not currently in RESERVED status.")
        previous_status = vehicle.status
        vehicle.status = VehicleUnit.STATUS_SOLD
        vehicle.full_clean()
        vehicle.save(update_fields=["status", "updated_at"])
        StockMovement.objects.create(
            vehicle=vehicle,
            movement_type=StockMovement.SOLD,
            from_location=vehicle.current_location,
            to_location=vehicle.current_location,
            reference_type="sale",
            reference_id=str(sale_reference).strip(),
            reason=locked.release_reason,
            performed_by=actor if getattr(actor, "pk", None) else None,
            metadata={"previous_status": previous_status},
        )
        vehicle_status_changed.send(
            sender=VehicleUnit,
            vehicle=vehicle,
            actor=actor,
            previous_status=previous_status,
            new_status=VehicleUnit.STATUS_SOLD,
            reason=locked.release_reason,
            request=request,
        )
        return locked
