"""Audit and business notifications for V07 domain events."""

from decimal import Decimal

from django.dispatch import receiver

from audit.services import AuditService
from core.events import (
    inventory_adjustment_created,
    inventory_created,
    inventory_submitted,
    inventory_validated,
    vehicle_blocked,
    vehicle_created,
    vehicle_delivered,
    vehicle_image_added,
    vehicle_price_changed,
    vehicle_received,
    vehicle_reservation_expired,
    vehicle_reservation_released,
    vehicle_reserved,
    vehicle_returned,
    vehicle_status_changed,
    vehicle_transferred,
    vehicle_unblocked,
    vehicle_updated,
)
from notifications.models import Notification
from notifications.services import NotificationService


def _decimal_text(value):
    """Render monetary values consistently without insignificant trailing zeros."""
    if value is None:
        return None
    amount = Decimal(str(value))
    if amount == 0:
        return "0"
    rendered = format(amount, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _audit(*, action, resource, actor=None, request=None, metadata=None, reason=""):
    AuditService.record(
        actor=actor,
        category="BUSINESS",
        action=action,
        resource=resource,
        status="success",
        reason=reason,
        request=request,
        metadata=metadata,
    )


@receiver(vehicle_created)
def audit_vehicle_created(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.created", resource=vehicle, actor=actor, request=request)


@receiver(vehicle_updated)
def audit_vehicle_updated(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.updated", resource=vehicle, actor=actor, request=request)


@receiver(vehicle_status_changed)
def audit_vehicle_status_changed(
    sender,
    vehicle,
    actor=None,
    previous_status="",
    new_status="",
    reason="",
    request=None,
    **kwargs,
):
    _audit(
        action="vehicle.status_changed",
        resource=vehicle,
        actor=actor,
        request=request,
        reason=reason,
        metadata={"previous_status": previous_status, "new_status": new_status},
    )


@receiver(vehicle_price_changed)
def audit_vehicle_price_changed(
    sender,
    vehicle,
    actor=None,
    old_price=None,
    new_price=None,
    old_currency="",
    new_currency="",
    reason="",
    request=None,
    **kwargs,
):
    _audit(
        action="vehicle.price_changed",
        resource=vehicle,
        actor=actor,
        request=request,
        reason=reason,
        metadata={
            "old_price": _decimal_text(old_price),
            "new_price": _decimal_text(new_price),
            "old_currency": old_currency,
            "new_currency": new_currency,
        },
    )


@receiver(vehicle_image_added)
def audit_vehicle_image_added(sender, image, vehicle, actor=None, request=None, **kwargs):
    _audit(
        action="vehicle.image_added",
        resource=vehicle,
        actor=actor,
        request=request,
        metadata={
            "image_id": image.pk,
            "mime_type": image.mime_type,
            "file_size": image.file_size,
            "checksum": image.checksum,
        },
    )


@receiver(vehicle_reserved)
def handle_vehicle_reserved(sender, reservation, vehicle, actor=None, request=None, **kwargs):
    _audit(
        action="vehicle.reserved",
        resource=reservation,
        actor=actor,
        request=request,
        metadata={
            "vehicle_id": vehicle.pk,
            "vehicle_reference": vehicle.stock_reference,
            "expires_at": reservation.expires_at.isoformat(),
        },
    )
    if reservation.reserved_by_id:
        NotificationService.notify(
            user=reservation.reserved_by,
            category=Notification.BUSINESS,
            code="vehicle.reservation.created",
            title="Vehicle reserved",
            message=f"Vehicle {vehicle.stock_reference} has been reserved for {reservation.customer.display_name}.",
            resource=reservation,
            data={"vehicle_id": vehicle.pk, "reservation_id": reservation.pk},
            idempotency_key=f"vehicle-reservation-created:{reservation.pk}",
        )


@receiver(vehicle_reservation_released)
def handle_vehicle_reservation_released(
    sender,
    reservation,
    vehicle,
    actor=None,
    request=None,
    **kwargs,
):
    _audit(
        action="vehicle.reservation_released",
        resource=reservation,
        actor=actor,
        request=request,
        metadata={"vehicle_id": vehicle.pk, "vehicle_reference": vehicle.stock_reference},
    )
    if reservation.reserved_by_id:
        NotificationService.notify(
            user=reservation.reserved_by,
            category=Notification.BUSINESS,
            code="vehicle.reservation.released",
            title="Vehicle reservation released",
            message=f"Reservation {reservation.reference} for vehicle {vehicle.stock_reference} has been released.",
            resource=reservation,
            data={"vehicle_id": vehicle.pk, "reservation_id": reservation.pk},
            idempotency_key=f"vehicle-reservation-released:{reservation.pk}",
        )


@receiver(vehicle_reservation_expired)
def handle_vehicle_reservation_expired(
    sender,
    reservation,
    vehicle,
    actor=None,
    request=None,
    **kwargs,
):
    _audit(
        action="vehicle.reservation_expired",
        resource=reservation,
        actor=actor,
        request=request,
        metadata={"vehicle_id": vehicle.pk, "vehicle_reference": vehicle.stock_reference},
    )
    if reservation.reserved_by_id:
        NotificationService.notify(
            user=reservation.reserved_by,
            category=Notification.BUSINESS,
            code="vehicle.reservation.expired",
            title="Vehicle reservation expired",
            message=f"Reservation {reservation.reference} for vehicle {vehicle.stock_reference} has expired.",
            resource=reservation,
            data={"vehicle_id": vehicle.pk, "reservation_id": reservation.pk},
            idempotency_key=f"vehicle-reservation-expired:{reservation.pk}",
        )


@receiver(vehicle_transferred)
def audit_vehicle_transferred(sender, vehicle, actor=None, from_location=None, to_location=None, request=None, **kwargs):
    _audit(
        action="vehicle.transferred",
        resource=vehicle,
        actor=actor,
        request=request,
        metadata={
            "from_location_id": getattr(from_location, "pk", None),
            "to_location_id": getattr(to_location, "pk", None),
        },
    )


@receiver(vehicle_blocked)
def audit_vehicle_blocked(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.blocked", resource=vehicle, actor=actor, request=request)


@receiver(vehicle_unblocked)
def audit_vehicle_unblocked(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.unblocked", resource=vehicle, actor=actor, request=request)


@receiver(vehicle_received)
def audit_vehicle_received(sender, vehicle, actor=None, previous_location=None, new_location=None, request=None, **kwargs):
    _audit(
        action="vehicle.received",
        resource=vehicle,
        actor=actor,
        request=request,
        metadata={
            "previous_location_id": getattr(previous_location, "pk", None),
            "new_location_id": getattr(new_location, "pk", None),
        },
    )


@receiver(vehicle_returned)
def audit_vehicle_returned(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.returned", resource=vehicle, actor=actor, request=request)


@receiver(vehicle_delivered)
def audit_vehicle_delivered(sender, vehicle, actor=None, request=None, **kwargs):
    _audit(action="vehicle.delivered", resource=vehicle, actor=actor, request=request)


@receiver(inventory_created)
def audit_inventory_created(sender, session, actor=None, expected_count=0, request=None, **kwargs):
    _audit(
        action="inventory.created",
        resource=session,
        actor=actor,
        request=request,
        metadata={"expected_count": expected_count, "location_id": session.location_id},
    )


@receiver(inventory_submitted)
def audit_inventory_submitted(sender, session, actor=None, request=None, **kwargs):
    _audit(action="inventory.submitted", resource=session, actor=actor, request=request)


@receiver(inventory_validated)
def audit_inventory_validated(sender, session, actor=None, anomaly_count=0, request=None, **kwargs):
    _audit(
        action="inventory.validated",
        resource=session,
        actor=actor,
        request=request,
        metadata={"anomaly_count": anomaly_count},
    )
    if session.started_by_id:
        NotificationService.notify(
            user=session.started_by,
            category=Notification.BUSINESS,
            code="vehicle.inventory.validated",
            title="Physical inventory validated",
            message=f"Inventory {session.reference} has been validated with {anomaly_count} anomaly(ies).",
            resource=session,
            data={"session_id": session.pk, "anomaly_count": anomaly_count},
            idempotency_key=f"vehicle-inventory-validated:{session.pk}",
        )
        if anomaly_count:
            NotificationService.notify(
                user=session.started_by,
                category=Notification.BUSINESS,
                code="vehicle.inventory.anomaly",
                title="Inventory anomalies detected",
                message=f"Inventory {session.reference} contains {anomaly_count} discrepancy line(s) requiring review.",
                resource=session,
                data={"session_id": session.pk, "anomaly_count": anomaly_count},
                idempotency_key=f"vehicle-inventory-anomaly:{session.pk}",
            )


@receiver(inventory_adjustment_created)
def audit_inventory_adjustment_created(sender, item, vehicle, movement, actor=None, request=None, **kwargs):
    _audit(
        action="inventory.adjustment_created",
        resource=vehicle,
        actor=actor,
        request=request,
        metadata={
            "inventory_item_id": item.pk,
            "stock_movement_id": movement.pk,
            "result": item.result,
        },
        reason=movement.reason,
    )
