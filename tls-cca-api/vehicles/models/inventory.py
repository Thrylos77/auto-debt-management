"""Physical stock inventory session and line models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.base_models import TimeStampedModel
from .vehicle import VehicleUnit


class InventorySession(TimeStampedModel):
    """Snapshot-based physical inventory session for one stock location."""

    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = (
        (DRAFT, "Draft"),
        (IN_PROGRESS, "In progress"),
        (SUBMITTED, "Submitted"),
        (VALIDATED, "Validated"),
        (CANCELLED, "Cancelled"),
    )

    reference = models.CharField(max_length=50, unique=True)
    location = models.ForeignKey(
        "vehicles.StockLocation",
        on_delete=models.PROTECT,
        related_name="inventory_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_inventory_sessions_started",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_inventory_sessions_validated",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["location"],
                condition=models.Q(
                    status__in=["DRAFT", "IN_PROGRESS", "SUBMITTED"]
                ),
                name="inv_one_open_location_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["location", "status"], name="inventory_location_status_idx"),
        ]

    def __str__(self):
        return f"{self.reference} — {self.location.code}"


class InventoryItem(TimeStampedModel):
    """Expected/observed inventory line with a derived discrepancy result."""

    session = models.ForeignKey(
        InventorySession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    vehicle = models.ForeignKey(
        "vehicles.VehicleUnit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_items",
    )
    expected_location = models.ForeignKey(
        "vehicles.StockLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_expected_items",
    )
    observed_location = models.ForeignKey(
        "vehicles.StockLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_observed_items",
    )
    expected_status = models.CharField(
        max_length=20,
        choices=VehicleUnit.STATUS_CHOICES,
        blank=True,
    )
    observed_status = models.CharField(
        max_length=20,
        choices=VehicleUnit.STATUS_CHOICES,
        blank=True,
    )
    found = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    scanned_reference = models.CharField(max_length=80, blank=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_inventory_items_scanned",
    )

    RESULT_MATCH = "MATCH"
    RESULT_LOCATION_MISMATCH = "LOCATION_MISMATCH"
    RESULT_STATUS_MISMATCH = "STATUS_MISMATCH"
    RESULT_MISSING = "MISSING"
    RESULT_UNEXPECTED = "UNEXPECTED"
    RESULT_CHOICES = (
        (RESULT_MATCH, "Match"),
        (RESULT_LOCATION_MISMATCH, "Location mismatch"),
        (RESULT_STATUS_MISMATCH, "Status mismatch"),
        (RESULT_MISSING, "Missing"),
        (RESULT_UNEXPECTED, "Unexpected"),
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "vehicle"],
                condition=models.Q(vehicle__isnull=False),
                name="inv_item_session_vehicle_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["session", "found"], name="inventory_item_found_idx"),
            models.Index(fields=["scanned_reference"], name="inventory_item_scan_ref_idx"),
        ]

    @property
    def result(self) -> str:
        if not self.found:
            return self.RESULT_MISSING
        if self.vehicle_id is None:
            return self.RESULT_UNEXPECTED
        if self.expected_location_id != self.session.location_id:
            return self.RESULT_UNEXPECTED
        if self.expected_location_id != self.observed_location_id:
            return self.RESULT_LOCATION_MISMATCH
        if self.expected_status != self.observed_status:
            return self.RESULT_STATUS_MISMATCH
        return self.RESULT_MATCH

    def clean(self):
        if self.found and (self.observed_location_id is None or not self.observed_status):
            raise ValidationError(
                "An observed location and status are required when an item is found."
            )

    def __str__(self):
        reference = self.scanned_reference or getattr(self.vehicle, "stock_reference", "unknown")
        return f"{self.session.reference} — {reference} — {self.result}"
