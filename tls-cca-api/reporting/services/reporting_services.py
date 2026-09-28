"""Reporting aggregation services."""

from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from receivables.models import Debt, Recovery, Term, TermStatus
from sales.models import CreditSale

from .dashboard_services import get_dashboard_stats


def get_global_dashboard_stats():
    """Return unrestricted reporting KPIs for authorized reporting views."""

    return get_dashboard_stats()


def get_aging_balance_report():
    """Generate the aging balance report."""

    today = timezone.now().date()
    unpaid_terms = Term.objects.exclude(
        term_status=TermStatus.PAID,
    ).annotate(
        due_amount=F("except_amount") - F("pay_amount"),
    )

    buckets = {
        "Not Due": {"min": -99999, "max": -1},
        "0-30 Days": {"min": 0, "max": 30},
        "30-60 Days": {"min": 31, "max": 60},
        "60-90 Days": {"min": 61, "max": 90},
        "90+ Days": {"min": 91, "max": 99999},
    }

    results = []
    total_overdue = 0

    for label, limits in buckets.items():
        min_date = today - timedelta(days=limits["max"])
        max_date = today - timedelta(days=limits["min"])

        if label == "90+ Days":
            queryset = unpaid_terms.filter(
                term_date__lt=today - timedelta(days=90),
            )
        elif label == "Not Due":
            queryset = unpaid_terms.filter(term_date__gt=today)
        else:
            queryset = unpaid_terms.filter(
                term_date__range=(min_date, max_date),
            )

        aggregate = queryset.aggregate(
            total=Coalesce(Sum("due_amount"), 0.0),
            count=Count("id"),
        )

        if label != "Not Due":
            total_overdue += float(aggregate["total"])

        results.append(
            {
                "bucket": label,
                "total_amount": aggregate["total"],
                "count": aggregate["count"],
            }
        )

    return {
        "generated_at": timezone.now(),
        "total_overdue": total_overdue,
        "buckets": results,
    }


def get_recovery_evolution():
    """Return recovery totals grouped by month."""

    evolution = (
        Recovery.objects.annotate(period=TruncMonth("recovery_date"))
        .values("period")
        .annotate(amount=Sum("amount"))
        .order_by("period")
    )

    return list(evolution)
