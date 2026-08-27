""" reporting/services/reporting_services.py """

from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone
from datetime import timedelta

from receivables.models import Debt, Recovery, Term, TermStatus
from sales.models import CreditSale

def get_global_dashboard_stats():
    """
    Calcule les KPIs globaux pour le tableau de bord.
    """
    sales_agg = CreditSale.objects.aggregate(total=Coalesce(Sum('total_amount'), 0.0))
    debt_agg = Debt.objects.aggregate(
        total_init=Coalesce(Sum('init_amount'), 0.0),
        total_balance=Coalesce(Sum('balance'), 0.0),
        active_count=Count('id', filter=Q(balance__gt=0))
    )
    recovery_agg = Recovery.objects.aggregate(total=Coalesce(Sum('amount'), 0.0))

    total_sales = sales_agg['total']
    total_init = debt_agg['total_init']
    total_balance = debt_agg['total_balance']
    total_recovered = recovery_agg['total']

    # Calculate Rate
    recovery_rate = 0.0
    if total_init > 0:
        recovery_rate = (float(total_recovered) / float(total_init)) * 100

    return {
        "total_sales": total_sales,
        "total_debt_initial": total_init,
        "total_debt_balance": total_balance,
        "total_recovered": total_recovered,
        "recovery_rate": round(recovery_rate, 2),
        "active_debtors_count": debt_agg['active_count']
    }

def get_aging_balance_report():
    """
    Génère les données pour la Balance Âgée.
    """
    today = timezone.now().date()
    
    # Get all unpaid or partially unpaid terms
    unpaid_terms = Term.objects.exclude(term_status=TermStatus.PAID).annotate(
        due_amount=F('except_amount') - F('pay_amount')
    )

    buckets = {
        "Not Due": {"min": -99999, "max": -1}, # Negative days overdue means future
        "0-30 Days": {"min": 0, "max": 30},
        "30-60 Days": {"min": 31, "max": 60},
        "60-90 Days": {"min": 61, "max": 90},
        "90+ Days": {"min": 91, "max": 99999},
    }

    results = []
    total_overdue = 0

    for label, limits in buckets.items():
        min_date = today - timedelta(days=limits['max'])
        max_date = today - timedelta(days=limits['min'])

        if label == "90+ Days":
            qs = unpaid_terms.filter(term_date__lt=today - timedelta(days=90))
        elif label == "Not Due":
            qs = unpaid_terms.filter(term_date__gt=today)
        else:
            qs = unpaid_terms.filter(term_date__range=(min_date, max_date))

        agg = qs.aggregate(total=Coalesce(Sum('due_amount'), 0.0), count=Count('id'))
        
        if label != "Not Due":
            total_overdue += float(agg['total'])

        results.append({
            "bucket": label,
            "total_amount": agg['total'],
            "count": agg['count']
        })

    return {
        "generated_at": timezone.now(),
        "total_overdue": total_overdue,
        "buckets": results
    }

def get_recovery_evolution():
    """
    Récupère l'évolution des recouvrements groupés par mois.
    """
    evolution = Recovery.objects.annotate(
        period=TruncMonth('recovery_date')
    ).values('period').annotate(
        amount=Sum('amount')
    ).order_by('period')

    return list(evolution)