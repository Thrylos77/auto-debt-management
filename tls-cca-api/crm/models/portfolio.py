"""Portfolio and portfolio-assignment journal models."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class Portfolio(models.Model):
    """Commercial portfolio grouping customers under an active owner."""

    ref = models.CharField(max_length=150, unique=True)
    commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="portfolios",
        null=True,
        blank=True,
        help_text="Portfolio commercial owner.",
    )
    description = models.TextField(blank=True)
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    active = models.BooleanField(default=True)
    last_transfer_date = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfolios"

    def __str__(self):
        if self.commercial:
            return (
                f"{self.ref} — "
                f"{self.commercial.get_full_name() or self.commercial.username}"
            )
        return self.ref


class PortfolioTransferQuerySet(models.QuerySet):
    """Prevent bulk mutations of the immutable transfer journal."""

    def update(self, **kwargs):
        raise RuntimeError("PortfolioTransfer is immutable.")

    def delete(self):
        raise RuntimeError("PortfolioTransfer is immutable.")


class PortfolioTransfer(models.Model):
    """Immutable journal entry for portfolio assignment and transfer."""

    objects = PortfolioTransferQuerySet.as_manager()

    portfolio = models.ForeignKey(
        "Portfolio",
        on_delete=models.PROTECT,
        related_name="transfers",
        help_text="The portfolio that was assigned/transferred.",
    )
    from_commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Previous commercial owner.",
    )
    to_commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="New commercial owner.",
    )
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="User who performed the assignment/transfer.",
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for the assignment/transfer.",
    )
    transferred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-transferred_at"]
        verbose_name = "Portfolio transfer"
        verbose_name_plural = "Portfolio transfers"

    def save(self, *args, **kwargs):
        """Keep the transfer journal append-only."""
        if self.pk is not None:
            raise RuntimeError("PortfolioTransfer is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent destructive deletion of the assignment journal."""
        raise RuntimeError("PortfolioTransfer is immutable.")

    def __str__(self):
        return f"{self.portfolio} → {self.to_commercial or 'unassigned'}"
