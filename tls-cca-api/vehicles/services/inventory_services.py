"""Transactional physical-inventory workflow services."""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.events import (
    inventory_adjustment_created,
    inventory_created,
    inventory_submitted,
    inventory_validated,
)

from vehicles.models import InventoryItem, InventorySession, StockMovement, StockLocation, VehicleUnit
from vehicles.policies import InventoryPolicy
from vehicles.services.stock_services import _apply_stock_adjustment


def _inventory_reference() -> str:
    from uuid import uuid4

    return f"INV-{uuid4().hex[:12].upper()}"


def start_inventory(*, session, actor, request=None):
    """Start an inventory and snapshot every vehicle expected at its location."""
    with transaction.atomic():
        locked_session = InventorySession.objects.select_for_update().get(pk=session.pk)
        if not InventoryPolicy.can_create(actor) and not InventoryPolicy.can_record(actor, locked_session):
            raise PermissionError("You do not have permission to start inventory.")
        if locked_session.status != InventorySession.DRAFT:
            raise ValidationError("Only draft inventories can be started.")

        now = timezone.now()
        locked_session.status = InventorySession.IN_PROGRESS
        locked_session.started_at = now
        locked_session.started_by = actor if getattr(actor, "pk", None) else None
        locked_session.full_clean()
        locked_session.save(update_fields=["status", "started_at", "started_by", "updated_at"])

        expected_vehicles = list(
            VehicleUnit.objects.filter(
                current_location=locked_session.location_id,
            ).exclude(status=VehicleUnit.STATUS_ARCHIVED)
        )
        existing_vehicle_ids = set(
            InventoryItem.objects.filter(session=locked_session).values_list("vehicle_id", flat=True)
        )
        items = []
        for vehicle in expected_vehicles:
            if vehicle.pk in existing_vehicle_ids:
                continue
            items.append(
                InventoryItem(
                    session=locked_session,
                    vehicle=vehicle,
                    expected_location=vehicle.current_location,
                    expected_status=vehicle.status,
                    found=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        if items:
            InventoryItem.objects.bulk_create(items, batch_size=500)

        return locked_session


def create_inventory_session(*, location, actor, notes="", request=None):
    """Create a draft inventory session for a stock location."""
    if not InventoryPolicy.can_create(actor):
        raise PermissionError("You do not have permission to create inventory sessions.")
    if not isinstance(location, StockLocation):
        location = StockLocation.objects.get(pk=location)
    if not location.is_active:
        raise ValidationError("An inventory can only be created for an active location.")

    session = InventorySession(
        reference=_inventory_reference(),
        location=location,
        status=InventorySession.DRAFT,
        notes=notes.strip(),
    )
    session.full_clean()
    session.save(force_insert=True)
    inventory_created.send(
        sender=InventorySession,
        session=session,
        actor=actor,
        expected_count=0,
        request=request,
    )
    return session


def record_inventory_item(
    *,
    session,
    actor,
    vehicle=None,
    scanned_reference="",
    observed_location,
    observed_status,
    notes="",
    request=None,
):
    """Record a physical observation against the start-time inventory snapshot."""
    with transaction.atomic():
        locked_session = InventorySession.objects.select_for_update().get(pk=session.pk)
        if not InventoryPolicy.can_record(actor, locked_session):
            raise PermissionError("You do not have permission to record inventory observations.")
        if locked_session.status != InventorySession.IN_PROGRESS:
            raise ValidationError("Inventory observations can only be recorded while the session is in progress.")

        target_location = StockLocation.objects.get(pk=getattr(observed_location, "pk", observed_location))
        if not target_location.is_active:
            raise ValidationError("Observed location is inactive.")
        if observed_status not in dict(VehicleUnit.STATUS_CHOICES):
            raise ValidationError({"observed_status": "Unsupported vehicle status."})

        resolved_vehicle = vehicle
        if resolved_vehicle is None and scanned_reference:
            resolved_vehicle = VehicleUnit.objects.filter(
                stock_reference__iexact=scanned_reference.strip()
            ).first()

        if resolved_vehicle is not None:
            resolved_vehicle = VehicleUnit.objects.get(pk=resolved_vehicle.pk)
            item = InventoryItem.objects.filter(
                session=locked_session,
                vehicle=resolved_vehicle,
            ).first()
            if item is None:
                item = InventoryItem(
                    session=locked_session,
                    vehicle=resolved_vehicle,
                    expected_location=resolved_vehicle.current_location,
                    expected_status=resolved_vehicle.status,
                )
            item.found = True
            item.observed_location = target_location
            item.observed_status = observed_status
            item.notes = (notes or "").strip()
            item.scanned_reference = (scanned_reference or resolved_vehicle.stock_reference).strip()
            item.scanned_at = timezone.now()
            item.scanned_by = actor
            item.full_clean()
            item.save()
            return item

        if not scanned_reference.strip():
            raise ValidationError({"scanned_reference": "A vehicle or scanned stock reference is required."})

        item = InventoryItem(
            session=locked_session,
            vehicle=None,
            found=True,
            observed_location=target_location,
            observed_status=observed_status,
            notes=(notes or "").strip(),
            scanned_reference=scanned_reference.strip(),
            scanned_at=timezone.now(),
            scanned_by=actor,
        )
        item.full_clean()
        item.save(force_insert=True)
        return item


def submit_inventory(*, session, actor, request=None):
    """Submit the frozen physical observations for review/validation."""
    with transaction.atomic():
        locked = InventorySession.objects.select_for_update().get(pk=session.pk)
        if not InventoryPolicy.can_submit(actor, locked):
            raise PermissionError("You do not have permission to submit inventory.")
        if locked.status != InventorySession.IN_PROGRESS:
            raise ValidationError("Only in-progress inventories can be submitted.")

        locked.status = InventorySession.SUBMITTED
        locked.completed_at = None
        locked.full_clean()
        locked.save(update_fields=["status", "completed_at", "updated_at"])
        inventory_submitted.send(sender=InventorySession, session=locked, actor=actor, request=request)
        return locked


def validate_inventory(*, session, actor, request=None):
    """Validate inventory findings without mutating stock."""
    with transaction.atomic():
        locked = InventorySession.objects.select_for_update().get(pk=session.pk)
        if not InventoryPolicy.can_validate(actor, locked):
            raise PermissionError("You do not have permission to validate inventory.")
        if locked.status != InventorySession.SUBMITTED:
            raise ValidationError("Only submitted inventories can be validated.")

        invalid_items = InventoryItem.objects.filter(
            session=locked,
            found=True,
        ).filter(
            models.Q(observed_location__isnull=True) | models.Q(observed_status="")
        )
        if invalid_items.exists():
            raise ValidationError("Inventory contains observations with missing location or status.")

        locked.status = InventorySession.VALIDATED
        locked.completed_at = timezone.now()
        locked.validated_by = actor if getattr(actor, "pk", None) else None
        locked.full_clean()
        locked.save(update_fields=["status", "completed_at", "validated_by", "updated_at"])
        anomaly_count = sum(
            1
            for item in InventoryItem.objects.filter(session=locked).select_related("session")
            if item.result != InventoryItem.RESULT_MATCH
        )
        inventory_validated.send(
            sender=InventorySession,
            session=locked,
            actor=actor,
            anomaly_count=anomaly_count,
            request=request,
        )
        return locked


def create_adjustment_from_inventory(*, item, actor, reason, request=None):
    """Explicitly correct a known inventory discrepancy; validation never does this automatically."""
    with transaction.atomic():
        locked_item = InventoryItem.objects.select_for_update().select_related("session").get(pk=item.pk)
        if not InventoryPolicy.can_adjust(actor, locked_item):
            raise PermissionError("You do not have permission to adjust inventory discrepancies.")
        if locked_item.session.status != InventorySession.VALIDATED:
            raise ValidationError("Inventory must be validated before a stock adjustment can be created.")
        if locked_item.vehicle_id is None:
            raise ValidationError("An unknown scanned reference cannot be adjusted until it is identified.")
        if locked_item.result == InventoryItem.RESULT_MATCH:
            raise ValidationError("The inventory item does not contain a discrepancy.")
        if StockMovement.objects.filter(
            movement_type=StockMovement.ADJUSTED,
            reference_type="inventory_item",
            reference_id=str(locked_item.pk),
        ).exists():
            raise ValidationError("An adjustment has already been created for this inventory item.")
        if not reason.strip():
            raise ValidationError({"reason": "An inventory adjustment requires a reason."})

        target_location = locked_item.observed_location if locked_item.result in {
            InventoryItem.RESULT_LOCATION_MISMATCH,
            InventoryItem.RESULT_UNEXPECTED,
        } else None
        new_status = locked_item.observed_status if locked_item.result == InventoryItem.RESULT_STATUS_MISMATCH else None
        vehicle, movement = _apply_stock_adjustment(
            vehicle=locked_item.vehicle,
            actor=actor,
            to_location=target_location,
            new_status=new_status,
            reason=reason,
            reference_type="inventory_item",
            reference_id=str(locked_item.pk),
            request=request,
        )
        inventory_adjustment_created.send(
            sender=InventoryItem,
            item=locked_item,
            vehicle=vehicle,
            movement=movement,
            actor=actor,
            request=request,
        )
        return movement
