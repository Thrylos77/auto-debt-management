"""Transactional services for receiving, transferring and adjusting stock."""

from django.core.exceptions import ValidationError
from django.db import transaction

from core.events import vehicle_blocked, vehicle_received, vehicle_transferred, vehicle_unblocked, vehicle_status_changed

from vehicles.models import StockLocation, StockMovement, VehicleReservation, VehicleUnit
from vehicles.policies import StockPolicy
from vehicles.services.vehicle_services import change_vehicle_status


def receive_vehicle(*, vehicle, location, actor, reason="", request=None):
    """Receive a vehicle into an active stock location."""
    if not StockPolicy.can_receive(actor):
        raise PermissionError("You do not have permission to receive vehicles into stock.")
    if not isinstance(location, StockLocation):
        location = StockLocation.objects.get(pk=location)

    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        target = StockLocation.objects.select_for_update().get(pk=location.pk)
        if not target.is_active:
            raise ValidationError("The target stock location is inactive.")
        if locked.status not in {VehicleUnit.STATUS_IN_STOCK, VehicleUnit.STATUS_RETURNED}:
            raise ValidationError("Only new/in-stock or returned vehicles can be received.")
        if locked.current_location_id == target.pk:
            raise ValidationError("Vehicle is already recorded at this location.")

        previous_location = locked.current_location
        previous_status = locked.status
        locked.current_location = target
        locked.status = VehicleUnit.STATUS_IN_STOCK
        locked.full_clean()
        locked.save(update_fields=["current_location", "status", "updated_at"])

        movement_type = StockMovement.RECEIVED
        StockMovement.objects.create(
            vehicle=locked,
            movement_type=movement_type,
            from_location=previous_location,
            to_location=target,
            reason=reason,
            performed_by=actor if getattr(actor, "pk", None) else None,
            metadata={"previous_status": previous_status, "new_status": locked.status},
        )
        if previous_status != locked.status:
            vehicle_status_changed.send(
                sender=VehicleUnit,
                vehicle=locked,
                actor=actor,
                previous_status=previous_status,
                new_status=locked.status,
                reason=reason,
                request=request,
            )
        vehicle_received.send(
            sender=VehicleUnit,
            vehicle=locked,
            actor=actor,
            previous_location=previous_location,
            new_location=target,
            request=request,
        )
        return locked


def transfer_vehicle(*, vehicle, to_location, actor, reason="", request=None):
    """Atomically move an in-stock vehicle and record the transfer."""
    if not StockPolicy.can_transfer(actor, vehicle):
        raise PermissionError("You do not have permission to transfer stock.")
    if not isinstance(to_location, StockLocation):
        to_location = StockLocation.objects.get(pk=to_location)

    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        target = StockLocation.objects.select_for_update().get(pk=to_location.pk)
        if not target.is_active:
            raise ValidationError("The destination stock location is inactive.")
        if locked.status != VehicleUnit.STATUS_IN_STOCK:
            raise ValidationError("Only vehicles currently in stock can be transferred.")
        if locked.current_location_id is None:
            raise ValidationError("Vehicle has no current stock location.")
        if locked.current_location_id == target.pk:
            raise ValidationError("Source and destination locations must differ.")

        previous_location = locked.current_location
        locked.current_location = target
        locked.full_clean()
        locked.save(update_fields=["current_location", "updated_at"])
        movement = StockMovement.objects.create(
            vehicle=locked,
            movement_type=StockMovement.TRANSFERRED,
            from_location=previous_location,
            to_location=target,
            reason=reason,
            performed_by=actor if getattr(actor, "pk", None) else None,
        )
        vehicle_transferred.send(
            sender=VehicleUnit,
            vehicle=locked,
            actor=actor,
            from_location=previous_location,
            to_location=target,
            movement=movement,
            request=request,
        )
        return locked


def block_vehicle(*, vehicle, actor, reason="", request=None):
    """Block a vehicle from reservation/sale availability."""
    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        if not StockPolicy._has(actor, "vehicle.change_status"):
            raise PermissionError("You do not have permission to change vehicle status.")
        if locked.status != VehicleUnit.STATUS_IN_STOCK:
            raise ValidationError("Only an in-stock vehicle can be blocked.")
        if VehicleReservation.objects.filter(
            vehicle=locked,
            status=VehicleReservation.ACTIVE,
        ).exists():
            raise ValidationError("An active reservation must be released before blocking the vehicle.")

        updated = change_vehicle_status(
            vehicle=locked,
            new_status=VehicleUnit.STATUS_BLOCKED,
            actor=actor,
            reason=reason,
            movement_type=StockMovement.BLOCKED,
            request=request,
        )
        vehicle_blocked.send(sender=VehicleUnit, vehicle=updated, actor=actor, request=request)
        return updated


def unblock_vehicle(*, vehicle, actor, reason="", request=None):
    """Return a blocked vehicle to normal stock availability."""
    if not StockPolicy._has(actor, "vehicle.change_status"):
        raise PermissionError("You do not have permission to unblock vehicles.")

    updated = change_vehicle_status(
        vehicle=vehicle,
        new_status=VehicleUnit.STATUS_IN_STOCK,
        actor=actor,
        reason=reason,
        movement_type=StockMovement.UNBLOCKED,
        request=request,
    )
    vehicle_unblocked.send(sender=VehicleUnit, vehicle=updated, actor=actor, request=request)
    return updated


def _apply_stock_adjustment(
    *,
    vehicle,
    actor,
    to_location=None,
    new_status=None,
    reason="",
    reference_type="",
    reference_id="",
    request=None,
):
    """Apply an already-authorized explicit stock adjustment."""
    if not reason.strip():
        raise ValidationError({"reason": "A stock adjustment requires a reason."})
    if to_location is None and new_status is None:
        raise ValidationError("An adjustment must change a location or status.")

    with transaction.atomic():
        locked = VehicleUnit.objects.select_for_update().get(pk=vehicle.pk)
        target = None
        if to_location is not None:
            target_id = getattr(to_location, "pk", to_location)
            target = StockLocation.objects.select_for_update().get(pk=target_id)
            if not target.is_active:
                raise ValidationError("The target stock location is inactive.")

        if new_status is not None and new_status not in dict(VehicleUnit.STATUS_CHOICES):
            raise ValidationError({"new_status": "Unsupported vehicle status."})
        if new_status == VehicleUnit.STATUS_RESERVED:
            raise ValidationError("Reservations must be managed by the reservation service.")

        previous_location = locked.current_location
        previous_status = locked.status
        if target is not None:
            locked.current_location = target
        if new_status is not None:
            locked.status = new_status
        locked.full_clean()
        locked.save(update_fields=["current_location", "status", "updated_at"])

        movement = StockMovement.objects.create(
            vehicle=locked,
            movement_type=StockMovement.ADJUSTED,
            from_location=previous_location,
            to_location=target or previous_location,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            performed_by=actor if getattr(actor, "pk", None) else None,
            metadata={
                "previous_status": previous_status,
                "new_status": locked.status,
            },
        )
        if previous_status != locked.status:
            vehicle_status_changed.send(
                sender=VehicleUnit,
                vehicle=locked,
                actor=actor,
                previous_status=previous_status,
                new_status=locked.status,
                reason=reason,
                request=request,
            )
        return locked, movement


def record_stock_adjustment(
    *,
    vehicle,
    actor,
    to_location=None,
    new_status=None,
    reason="",
    reference_type="",
    reference_id="",
    request=None,
):
    """Apply an explicit stock adjustment after checking the stock-adjust permission."""
    if not StockPolicy.can_adjust(actor, vehicle):
        raise PermissionError("You do not have permission to adjust stock.")
    return _apply_stock_adjustment(
        vehicle=vehicle,
        actor=actor,
        to_location=to_location,
        new_status=new_status,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        request=request,
    )
