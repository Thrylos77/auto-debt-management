"""Customer and person-detail domain models for CRM."""

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.utils.validators import phone_validator


country_code_validator = RegexValidator(
    regex=r"^[A-Z]{2}$",
    message="Country code must use the ISO 3166-1 alpha-2 format.",
)


class Customer(models.Model):
    """CRM customer aggregate root shared by physical and moral persons."""

    TYPE_PHYSICAL = "physical"
    TYPE_MORAL = "moral"
    TYPE_CHOICES = [
        (TYPE_PHYSICAL, "Physical"),
        (TYPE_MORAL, "Moral"),
    ]

    CONTACT_EMAIL = "email"
    CONTACT_PHONE = "phone"
    CONTACT_MOBILE = "mobile"
    CONTACT_CHOICES = [
        (CONTACT_EMAIL, "Email"),
        (CONTACT_PHONE, "Phone"),
        (CONTACT_MOBILE, "Mobile"),
    ]

    LIFECYCLE_PROSPECT = "prospect"
    LIFECYCLE_ACTIVE = "active"
    LIFECYCLE_SUSPENDED = "suspended"
    LIFECYCLE_INACTIVE = "inactive"
    LIFECYCLE_BLOCKED = "blocked"
    LIFECYCLE_ARCHIVED = "archived"
    LIFECYCLE_CHOICES = [
        (LIFECYCLE_PROSPECT, "Prospect"),
        (LIFECYCLE_ACTIVE, "Active"),
        (LIFECYCLE_SUSPENDED, "Suspended"),
        (LIFECYCLE_INACTIVE, "Inactive"),
        (LIFECYCLE_BLOCKED, "Blocked"),
        (LIFECYCLE_ARCHIVED, "Archived"),
    ]

    customer_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_PHYSICAL,
    )
    portfolio = models.ForeignKey(
        "Portfolio",
        on_delete=models.PROTECT,
        related_name="customers",
        null=True,
        blank=True,
        help_text="Portfolio this customer belongs to.",
    )

    # Contact information.
    email = models.EmailField(blank=True)
    secondary_email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, validators=[phone_validator])
    mobile = models.CharField(
        max_length=30,
        blank=True,
        validators=[phone_validator],
    )
    preferred_contact_channel = models.CharField(
        max_length=10,
        choices=CONTACT_CHOICES,
        default=CONTACT_PHONE,
    )

    # Keep the legacy free-text address during the V6 compatibility period.
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Kept temporarily for backward compatibility with existing consumers.
    # Lifecycle operations keep this flag synchronized with lifecycle_status.
    is_active = models.BooleanField(default=True)
    lifecycle_status = models.CharField(
        max_length=20,
        choices=LIFECYCLE_CHOICES,
        default=LIFECYCLE_ACTIVE,
        db_index=True,
    )
    status_changed_at = models.DateTimeField(default=timezone.now, db_index=True)
    status_changed_by_id = models.PositiveBigIntegerField(null=True, blank=True)
    status_reason = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self) -> str:
        """Return the most useful human-readable name for the customer."""
        try:
            physical_detail = self.physical_detail
        except ObjectDoesNotExist:
            physical_detail = None
        except Exception:
            physical_detail = None

        if physical_detail and (
            physical_detail.first_name or physical_detail.last_name
        ):
            return (
                f"{physical_detail.first_name or ''} "
                f"{physical_detail.last_name or ''}"
            ).strip()

        try:
            moral_detail = self.moral_detail
        except ObjectDoesNotExist:
            moral_detail = None
        except Exception:
            moral_detail = None

        if moral_detail and moral_detail.business_name:
            return moral_detail.business_name

        if self.email:
            return self.email
        if self.phone:
            return self.phone
        return f"Customer #{self.pk or 'unsaved'}"


class CustomerAddress(models.Model):
    """Structured address associated with a CRM customer."""

    ADDRESS_LEGAL = "legal"
    ADDRESS_RESIDENTIAL = "residential"
    ADDRESS_BILLING = "billing"
    ADDRESS_DELIVERY = "delivery"
    ADDRESS_OTHER = "other"
    ADDRESS_TYPE_CHOICES = [
        (ADDRESS_LEGAL, "Legal"),
        (ADDRESS_RESIDENTIAL, "Residential"),
        (ADDRESS_BILLING, "Billing"),
        (ADDRESS_DELIVERY, "Delivery"),
        (ADDRESS_OTHER, "Other"),
    ]

    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default=ADDRESS_OTHER,
    )
    label = models.CharField(max_length=100, blank=True, default="")
    address_line_1 = models.CharField(max_length=255, blank=True, default="")
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    neighborhood = models.CharField(max_length=150, blank=True, default="")
    city = models.CharField(max_length=150, blank=True, default="")
    state_region = models.CharField(max_length=150, blank=True, default="")
    postal_code = models.CharField(max_length=30, blank=True, default="")
    country = models.CharField(max_length=150, blank=True, default="")
    country_code = models.CharField(
        max_length=2,
        blank=True,
        default="",
        validators=[country_code_validator],
        help_text="ISO 3166-1 alpha-2 country code.",
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Normalize country codes before persistence."""
        if self.country_code:
            self.country_code = self.country_code.upper()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-is_primary", "-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(is_primary=True),
                name="crm_customer_one_primary_address",
            ),
        ]
        indexes = [
            models.Index(
                fields=["customer", "address_type"],
                name="crm_address_customer_type_idx",
            ),
        ]
        verbose_name = "Customer address"
        verbose_name_plural = "Customer addresses"

    def __str__(self):
        location = ", ".join(
            value
            for value in (self.neighborhood, self.city, self.country)
            if value
        )
        return location or self.address_line_1 or f"Address #{self.pk or 'unsaved'}"


class PhysicalPersonDetail(models.Model):
    """Professional identity profile for a physical-person customer."""

    customer = models.OneToOneField(
        "Customer",
        on_delete=models.CASCADE,
        related_name="physical_detail",
    )

    # Identity.
    first_name = models.CharField(max_length=150, blank=True, default="")
    middle_names = models.CharField(max_length=200, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    preferred_name = models.CharField(max_length=150, blank=True, default="")

    # Birth and nationality.
    birth_day = models.DateField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, default="")
    birth_city = models.CharField(max_length=150, blank=True, default="")
    birth_country = models.CharField(max_length=150, blank=True, default="")
    nationality = models.CharField(max_length=100, blank=True, default="")

    # Identity document.
    id_document_type = models.CharField(max_length=50, blank=True, default="")
    id_document_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Identity document or passport number.",
    )
    id_document_issuing_authority = models.CharField(max_length=255, blank=True, default="")
    id_document_issuer_country = models.CharField(max_length=150, blank=True, default="")
    id_document_issued_at = models.DateField(blank=True, null=True)
    id_document_expires_at = models.DateField(blank=True, null=True)

    # Professional profile.
    occupation = models.CharField(max_length=150, blank=True, default="")
    employer_name = models.CharField(max_length=255, blank=True, default="")

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Physical person detail"
        verbose_name_plural = "Physical person details"

    def __str__(self):
        return f"Physical details for {self.customer}"


class MoralPersonDetail(models.Model):
    """Professional legal and operational profile for a moral-person customer."""

    customer = models.OneToOneField(
        "Customer",
        on_delete=models.CASCADE,
        related_name="moral_detail",
    )

    # Legal identity.
    business_name = models.CharField(max_length=255, blank=True, default="")
    trading_name = models.CharField(max_length=255, blank=True, default="")
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Company registration or registry number.",
    )
    tax_identification_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Tax identification number.",
    )
    legal_form = models.CharField(max_length=100, blank=True, default="")
    incorporation_date = models.DateField(blank=True, null=True)
    registration_country = models.CharField(max_length=150, blank=True, default="")

    # Business activity.
    activity_sector = models.CharField(max_length=150, blank=True, default="")
    primary_activity = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, default="")

    # Legal representative.
    representative_first_name = models.CharField(max_length=150, blank=True, default="")
    representative_last_name = models.CharField(max_length=150, blank=True, default="")
    representative_function = models.CharField(max_length=150, blank=True, default="")
    representative_id_document_type = models.CharField(max_length=50, blank=True, default="")
    representative_id_document = models.CharField(max_length=100, blank=True, default="")
    representative_id_issuer_country = models.CharField(max_length=150, blank=True, default="")
    representative_id_issued_at = models.DateField(blank=True, null=True)
    representative_id_expires_at = models.DateField(blank=True, null=True)
    representative_email = models.EmailField(blank=True, default="")
    representative_phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[phone_validator],
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Moral person detail"
        verbose_name_plural = "Moral person details"

    def save(self, *args, **kwargs):
        if self.registration_number == "":
            self.registration_number = None
        if self.tax_identification_number == "":
            self.tax_identification_number = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name or f"Moral details for {self.customer}"
