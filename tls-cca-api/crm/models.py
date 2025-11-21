""" CRM Models"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from simple_history.models import HistoricalRecords
from django.core.validators import MinValueValidator
from core.utils.validators import phone_validator


class Customer(models.Model):
    TYPE_PHYSICAL = 'physical'
    TYPE_MORAL = 'moral'
    TYPE_CHOICES = [
        (TYPE_PHYSICAL, 'Physical'),
        (TYPE_MORAL, 'Moral'),
    ]

    # Basic Info
    customer_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_PHYSICAL)
    portfolio = models.ForeignKey(
        'Portfolio', on_delete=models.PROTECT, 
        related_name='customers', null=True, blank=True,
        help_text="Portfolio this customer belongs to"
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True, validators=[phone_validator])
    mobile = models.CharField(max_length=30, blank=True, null=True, validators=[phone_validator])
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    def __str__(self):
        return self.display_name

    @property
    def display_name(self) -> str:
        """
        Returns a readable display name for admin/logs.
        Priority: Physical person (first name + last name) > Moral person (business_name) > email > phone > fallback.
        """
        # Physical detail (OneToOne) — protected access against DoesNotExist
        try: pd = self.physical_detail
        except ObjectDoesNotExist: pd = None
        except Exception: pd = None

        if pd and (pd.first_name or pd.last_name):
            return f"{pd.first_name or ''} {pd.last_name or ''}".strip()

        # Moral detail
        try: md = self.moral_detail
        except ObjectDoesNotExist: md = None
        except Exception: md = None

        if md and md.business_name: return md.business_name

        # Fallbacks
        if self.email: return self.email
        if self.phone: return self.phone
        return f"Customer #{self.pk or 'unsaved'}"

class PhysicalPersonDetail(models.Model):
    customer = models.OneToOneField('Customer', on_delete=models.CASCADE, related_name='physical_detail')
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    birth_day = models.DateField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True)
    id_document_type = models.CharField(max_length=50, blank=True)
    id_document_number = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text='ID/Passport number (unique if provided)'
    )
    nationality = models.CharField(max_length=100, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Physical person detail"
        verbose_name_plural = "Physical person details"

    def __str__(self):
        # Initialy show the customer name
        return f"Physical details for {self.customer}"

class MoralPersonDetail(models.Model):
    customer = models.OneToOneField('Customer', on_delete=models.CASCADE, related_name='moral_detail')
    business_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(
        max_length=20, blank=True, unique=True, 
        help_text="SIRET/NIF/Registry number (unique if provided)"
    )
    legal_form = models.CharField(max_length=100, blank=True)
    representative_first_name = models.CharField(max_length=150, blank=True)
    representative_last_name = models.CharField(max_length=150, blank=True)
    representative_id_document = models.CharField(max_length=100, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Moral person detail"
        verbose_name_plural = "Moral person details"

    def __str__(self):
        return self.business_name or f"Moral details for {self.customer}"

class Portfolio(models.Model):
    name = models.CharField(max_length=150, unique=True)
    commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='portfolios', 
        null=True, blank=True, help_text='Portfolio commercial owner'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'

    def __str__(self):
        if self.commercial:
            return f"{self.name} — {self.commercial.get_full_name() or self.commercial.username}"
        return self.name