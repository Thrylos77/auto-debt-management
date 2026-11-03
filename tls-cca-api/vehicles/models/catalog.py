"""Automotive catalogue models shared by physical vehicle units."""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.base_models import TimeStampedModel


class VehicleCategory(TimeStampedModel):
    """Hierarchical business category for automotive assets."""

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="vehicle_cat_parent_idx"),
        ]

    def clean(self):
        if self.parent_id == self.pk:
            raise ValidationError({"parent": "A category cannot be its own parent."})

        ancestor = self.parent
        visited = set()
        while ancestor is not None:
            if ancestor.pk in visited:
                raise ValidationError({"parent": "Category hierarchy contains a cycle."})
            visited.add(ancestor.pk)
            if ancestor.pk == self.pk:
                raise ValidationError({"parent": "Category hierarchy contains a cycle."})
            ancestor = ancestor.parent

    def __str__(self):
        return f"{self.code} — {self.name}"


class VehicleBrand(TimeStampedModel):
    """Automotive manufacturer or brand."""

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="vehicle_brand_active_idx"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class VehicleModel(TimeStampedModel):
    """Commercial model belonging to a brand."""

    brand = models.ForeignKey(
        VehicleBrand,
        on_delete=models.PROTECT,
        related_name="models",
    )
    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_models",
    )
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["brand__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["brand", "code"],
                name="vehicle_model_brand_code_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["brand", "is_active"], name="vehicle_model_brand_idx"),
            models.Index(fields=["category", "is_active"], name="vehicle_model_category_idx"),
        ]

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class VehicleVariant(TimeStampedModel):
    """Commercial/technical variant shared by multiple physical units."""

    FUEL_PETROL = "PETROL"
    FUEL_DIESEL = "DIESEL"
    FUEL_HYBRID = "HYBRID"
    FUEL_ELECTRIC = "ELECTRIC"
    FUEL_LPG = "LPG"
    FUEL_CNG = "CNG"
    FUEL_OTHER = "OTHER"
    FUEL_TYPE_CHOICES = (
        (FUEL_PETROL, "Petrol"),
        (FUEL_DIESEL, "Diesel"),
        (FUEL_HYBRID, "Hybrid"),
        (FUEL_ELECTRIC, "Electric"),
        (FUEL_LPG, "LPG"),
        (FUEL_CNG, "CNG"),
        (FUEL_OTHER, "Other"),
    )

    TRANSMISSION_MANUAL = "MANUAL"
    TRANSMISSION_AUTOMATIC = "AUTOMATIC"
    TRANSMISSION_CVT = "CVT"
    TRANSMISSION_OTHER = "OTHER"
    TRANSMISSION_CHOICES = (
        (TRANSMISSION_MANUAL, "Manual"),
        (TRANSMISSION_AUTOMATIC, "Automatic"),
        (TRANSMISSION_CVT, "CVT"),
        (TRANSMISSION_OTHER, "Other"),
    )

    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name="variants",
    )
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=180)
    engine_description = models.CharField(max_length=255, blank=True)
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        blank=True,
    )
    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        blank=True,
    )
    seats = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    power_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    power_unit = models.CharField(max_length=20, blank=True)
    technical_specs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["model__brand__name", "model__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "code"],
                name="vehicle_variant_model_code_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["model", "is_active"], name="vehicle_variant_model_idx"),
        ]

    def __str__(self):
        return f"{self.model} — {self.name}"
