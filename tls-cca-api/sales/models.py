""" Sales Models """
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords
from django.utils.translation import gettext_lazy as _

from crm.models import Customer, Portfolio

class CreditSaleStatus(models.TextChoices):
    PENDING_APPROVAL = 'pending_approval', _('Pending Approval')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    CANCELLED = 'cancelled', _('Cancelled')

class CreditSale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    commercial = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.PROTECT,
        related_name='sales', null=True, blank=True,
        help_text="Portfolio this sale belongs to. If not set, commercial's first portfolio is used."
    )
    sale_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    status = models.CharField(max_length=30, choices=CreditSaleStatus.choices, default=CreditSaleStatus.PENDING_APPROVAL)
    proof_doc = models.FileField(upload_to='docs/sales/', null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Credit sale"
        verbose_name_plural = "Credit sales"
        ordering = ['-sale_date']

    def save(self, *args, **kwargs):
        # if no portfolio assigned, attempt to use first portfolio of commercial
        if not self.portfolio and self.commercial:
            default_pf_qs = getattr(self.commercial, 'portfolios', None)
            if default_pf_qs:
                first_pf = default_pf_qs.first()
                if first_pf:
                    self.portfolio = first_pf
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale #{self.pk or 'unsaved'} - {self.customer.display_name} ({self.total_amount})"