""" Receivables Models """
from datetime import date
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

class DebtStatus(models.TextChoices):
    ONGOING = 'ongoing', _('Ongoing')
    PAID = 'paid', _('Paid')
    LATE = 'late', _('Late')

class TermStatus(models.TextChoices):
    NOT_RECEIVED = 'not_received', _('Not Received')
    RECEIVED = 'received', _('Received')
    LATE = 'late', _('Late')

class RecoveryPaymentMode(models.TextChoices):
    CASH = 'cash', _('Cash')
    CREDIT_CARD = 'credit_card', _('Credit Card')
    BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
    CHECK = 'check', _('Check')
    OTHER = 'other', _('Other')

# Créance
class Debt(models.Model):
    sale = models.OneToOneField('sales.CreditSale', on_delete=models.CASCADE, related_name='debts')
    init_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    start_date = models.DateField(null=True, default=date.today)
    close_date = models.DateField(null=True, blank=True)
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0,  validators=[MinValueValidator(0)])
    month_duration = models.PositiveIntegerField(default=1)
    regulation_mode = models.CharField(max_length=50)
    debt_status = models.CharField(max_length=20, choices=DebtStatus.choices, default=DebtStatus.ONGOING)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Debt"
        verbose_name_plural = "Debts"
        ordering = ['-start_date']

    def __str__(self):
        return f"Debt for sale #{self.sale.pk} ({self.balance}/{self.init_amount})"

# Echéances
class Term(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='terms')
    term_date = models.DateField(null=True)
    except_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateTimeField(null=True, blank=True)
    term_status = models.CharField(max_length=20, choices=TermStatus.choices, default=TermStatus.NOT_RECEIVED)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Term"
        verbose_name_plural = "Terms"
        ordering = ['term_date']

    def __str__(self):
        return f"Term on {self.term_date} for debt #{self.debt.pk}"


# Recouvrement
class Recovery(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='recoveries')
    commercial = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    payment_mode = models.CharField(max_length=50, choices=RecoveryPaymentMode.choices, default=RecoveryPaymentMode.CASH)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Recovery"
        verbose_name_plural = "Recoveries"
        ordering = ['-date']

    def __str__(self):
        return f"Recovery #{self.pk} - {self.amount} on {self.date}"