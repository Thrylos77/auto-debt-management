""" Sales Models """
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords

from crm.models import Customer

class CreditSale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    commercial = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    status = models.CharField(max_length=30, default='ongoing')
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