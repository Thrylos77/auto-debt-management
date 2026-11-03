"""Stock locations and immutable vehicle movement journal."""

from django.db import models
from django.conf import settings

from core.base_models import TimeStampedModel


class StockMovementQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("StockMovement is append-only.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("StockMovement is append-only.")

    def bulk_update(self, *args, **kwargs):
        raise RuntimeError("StockMovement is append-only.")


class StockMovementManager(models.Manager.from_queryset(StockMovementQuerySet)):
    """Manager for immutable stock movement entries."""


class StockLocation(TimeStampedModel):
    """Physical location where vehicle units can be held."""

    TYPE_SHOWROOM = "SHOWROOM"
    TYPE_YARD = "YARD"
    TYPE_WAREHOUSE = "WAREHOUSE"
    TYPE_BRANCH = "BRANCH"
    TYPE_OTHER = "OTHER"
    TYPE_CHOICES = (
        (TYPE_SHOWROOM, "Showroom"),
        (TYPE_YARD, "Yard"),
        (TYPE_WAREHOUSE, "Warehouse"),
        (TYPE_BRANCH, "Branch"),
        (TYPE_OTHER, "Other"),
    )

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["type", "is_active"], name="stock_location_type_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class StockMovement(models.Model):
    """Append-only operational journal for stock state/location changes."""

    RECEIVED = "RECEIVED"
    TRANSFERRED = "TRANSFERRED"
    RESERVED = "RESERVED"
    RELEASED = "RELEASED"
    SOLD = "SOLD"
    RETURNED = "RETURNED"
    BLOCKED = "BLOCKED"
    UNBLOCKED = "UNBLOCKED"
    ADJUSTED = "ADJUSTED"
    DELIVERED = "DELIVERED"
    MOVEMENT_TYPE_CHOICES = (
        (RECEIVED, "Received"),
        (TRANSFERRED, "Transferred"),
        (RESERVED, "Reserved"),
        (RELEASED, "Released"),
        (SOLD, "Sold"),
        (RETURNED, "Returned"),
        (BLOCKED, "Blocked"),
        (UNBLOCKED, "Unblocked"),
        (ADJUSTED, "Adjusted"),
        (DELIVERED, "Delivered"),
    )

    vehicle = models.ForeignKey(
        "vehicles.VehicleUnit",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    from_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_movements",
    )
    to_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_movements",
    )
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_stock_movements",
    )
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = StockMovementManager()

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["vehicle", "occurred_at"], name="stock_move_vehicle_time_idx"),
            models.Index(fields=["movement_type", "occurred_at"], name="stock_move_type_time_idx"),
            models.Index(fields=["reference_type", "reference_id"], name="stock_move_reference_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("StockMovement is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("StockMovement is append-only.")

    def __str__(self):
        return f"{self.vehicle.stock_reference} — {self.movement_type}"
