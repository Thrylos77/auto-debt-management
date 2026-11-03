"""Physical vehicle units and their commercial price/image metadata."""

import hashlib
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.base_models import TimeStampedModel


def generate_stock_reference() -> str:
    """Generate a non-sensitive human-readable stock reference."""
    return f"VH-{uuid.uuid4().hex[:16].upper()}"


def vehicle_image_upload_to(instance, filename: str) -> str:
    """Store images below the stock reference with a server-selected extension."""
    suffix_by_mime = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    suffix = suffix_by_mime.get(getattr(instance, "mime_type", ""), "bin")
    return f"vehicles/images/{instance.vehicle.stock_reference}/{uuid.uuid4().hex}.{suffix}"


class VehicleUnit(TimeStampedModel):
    """One physical automotive asset held by the concession."""

    CONDITION_NEW = "NEW"
    CONDITION_USED = "USED"
    CONDITION_RECONDITIONED = "RECONDITIONED"
    CONDITION_DAMAGED = "DAMAGED"
    CONDITION_OTHER = "OTHER"
    CONDITION_CHOICES = (
        (CONDITION_NEW, "New"),
        (CONDITION_USED, "Used"),
        (CONDITION_RECONDITIONED, "Reconditioned"),
        (CONDITION_DAMAGED, "Damaged"),
        (CONDITION_OTHER, "Other"),
    )

    STATUS_IN_STOCK = "IN_STOCK"
    STATUS_RESERVED = "RESERVED"
    STATUS_SOLD = "SOLD"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_BLOCKED = "BLOCKED"
    STATUS_RETURNED = "RETURNED"
    STATUS_ARCHIVED = "ARCHIVED"
    STATUS_CHOICES = (
        (STATUS_IN_STOCK, "In stock"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_SOLD, "Sold"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_BLOCKED, "Blocked"),
        (STATUS_RETURNED, "Returned"),
        (STATUS_ARCHIVED, "Archived"),
    )

    MILEAGE_KM = "KM"
    MILEAGE_MILES = "MILES"
    MILEAGE_UNIT_CHOICES = (
        (MILEAGE_KM, "Kilometres"),
        (MILEAGE_MILES, "Miles"),
    )

    stock_reference = models.CharField(
        max_length=40,
        unique=True,
        default=generate_stock_reference,
        editable=False,
    )
    variant = models.ForeignKey(
        "vehicles.VehicleVariant",
        on_delete=models.PROTECT,
        related_name="vehicle_units",
    )
    vin = models.CharField(max_length=32, null=True, blank=True)
    chassis_number = models.CharField(max_length=100, null=True, blank=True)
    engine_number = models.CharField(max_length=100, null=True, blank=True)
    registration_number = models.CharField(max_length=50, null=True, blank=True)
    manufacture_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1886), MaxValueValidator(2200)],
    )
    model_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1886), MaxValueValidator(2200)],
    )
    color = models.CharField(max_length=80, blank=True)
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default=CONDITION_NEW,
    )
    mileage = models.PositiveBigIntegerField(default=0)
    mileage_unit = models.CharField(
        max_length=10,
        choices=MILEAGE_UNIT_CHOICES,
        default=MILEAGE_KM,
    )
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(max_length=3, default="XAF")
    current_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_STOCK,
        db_index=True,
    )
    current_location = models.ForeignKey(
        "vehicles.StockLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_vehicle_units",
    )
    is_catalog_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vin"],
                condition=models.Q(vin__isnull=False),
                name="vehicle_unit_vin_uq",
            ),
            models.UniqueConstraint(
                fields=["chassis_number"],
                condition=models.Q(chassis_number__isnull=False),
                name="vehicle_unit_chassis_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["variant", "status"], name="vehicle_unit_variant_idx"),
            models.Index(fields=["status", "current_location"], name="vehicle_unit_stock_idx"),
            models.Index(fields=["manufacture_year"], name="vehicle_unit_mfg_year_idx"),
            models.Index(fields=["current_price"], name="vehicle_unit_price_idx"),
        ]

    def clean(self):
        # These identifiers are nullable in the database, so an empty value is
        # represented by None. Color is deliberately non-nullable and uses an
        # empty string when it is not provided.
        for field_name in ("vin", "chassis_number", "engine_number", "registration_number"):
            value = getattr(self, field_name, None)
            if isinstance(value, str):
                normalized = value.strip()
                setattr(self, field_name, normalized or None)

        self.color = (self.color or "").strip()

        currency = (self.currency or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValidationError({"currency": "Currency must be a three-letter ISO-style code."})
        self.currency = currency

        if self.acquisition_date and self.acquisition_date > timezone.localdate():
            raise ValidationError({"acquisition_date": "Acquisition date cannot be in the future."})

        if (
            self.manufacture_year
            and self.model_year
            and self.model_year < self.manufacture_year - 1
        ):
            raise ValidationError(
                {"model_year": "Model year is inconsistent with the manufacture year."}
            )

    def __str__(self):
        return f"{self.stock_reference} — {self.variant}"


class VehicleImage(TimeStampedModel):
    """Validated image attached to a physical vehicle unit."""

    vehicle = models.ForeignKey(
        VehicleUnit,
        on_delete=models.PROTECT,
        related_name="images",
    )
    file = models.ImageField(upload_to=vehicle_image_upload_to)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_images_uploaded",
    )
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(is_primary=True),
                name="vehicle_image_one_primary_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["vehicle", "sort_order"], name="vimg_vehicle_order_idx"),
            models.Index(fields=["checksum"], name="vehicle_image_checksum_idx"),
        ]

    def __str__(self):
        return f"Image #{self.pk or 'new'} — {self.vehicle.stock_reference}"

    @staticmethod
    def checksum_for(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class VehiclePriceHistoryQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("VehiclePriceHistory is append-only.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("VehiclePriceHistory is append-only.")

    def bulk_update(self, *args, **kwargs):
        raise RuntimeError("VehiclePriceHistory is append-only.")


class VehiclePriceHistoryManager(models.Manager.from_queryset(VehiclePriceHistoryQuerySet)):
    """Manager for immutable price history entries."""


class VehiclePriceHistory(models.Model):
    """Append-only before/after record of vehicle price changes."""

    vehicle = models.ForeignKey(
        VehicleUnit,
        on_delete=models.PROTECT,
        related_name="price_history",
    )
    old_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    new_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(max_length=3)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_price_changes",
    )
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = VehiclePriceHistoryManager()

    class Meta:
        ordering = ["-changed_at", "-id"]
        indexes = [
            models.Index(fields=["vehicle", "changed_at"], name="vehicle_price_history_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("VehiclePriceHistory is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("VehiclePriceHistory is append-only.")

    def __str__(self):
        return f"{self.vehicle.stock_reference}: {self.old_price} → {self.new_price} {self.currency}"
