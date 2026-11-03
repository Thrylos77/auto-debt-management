"""Vehicle reservation lifecycle models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.base_models import TimeStampedModel


class VehicleReservation(TimeStampedModel):
    """Time-bound reservation of one physical vehicle unit for a customer."""

    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    CONVERTED_TO_SALE = "CONVERTED_TO_SALE"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = (
        (ACTIVE, "Active"),
        (RELEASED, "Released"),
        (EXPIRED, "Expired"),
        (CONVERTED_TO_SALE, "Converted to sale"),
        (CANCELLED, "Cancelled"),
    )

    reference = models.CharField(max_length=50, unique=True)
    vehicle = models.ForeignKey(
        "vehicles.VehicleUnit",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        related_name="vehicle_reservations",
    )
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vehicle_reservations_created",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        db_index=True,
    )
    reserved_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_reservations_released",
    )
    release_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-reserved_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(status="ACTIVE"),
                name="vres_one_active_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["vehicle", "status"], name="vres_vehicle_status_idx"),
            models.Index(fields=["status", "expires_at"], name="vres_status_expiry_idx"),
            models.Index(fields=["customer", "reserved_at"], name="vres_customer_time_idx"),
        ]

    def clean(self):
        if self.status == self.ACTIVE:
            if self.expires_at is None:
                raise ValidationError({"expires_at": "Active reservations require an expiration date."})
            if self.expires_at <= self.reserved_at:
                raise ValidationError({"expires_at": "Expiration must be later than reservation time."})

    @property
    def is_expired(self) -> bool:
        return self.status == self.ACTIVE and self.expires_at <= timezone.now()

    def __str__(self):
        return f"{self.reference} — {self.vehicle.stock_reference}"
