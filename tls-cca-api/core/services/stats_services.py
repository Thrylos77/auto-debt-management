from django.db.models import Sum, Q, Count
from django.db.models.functions import Coalesce, TruncMonth
from sales.models import CreditSale, CreditSaleStatus
from receivables.models import Debt, DebtStatus, Recovery

def get_global_stats(user):
    """
    Aggregates global statistics (KPIs) for the dashboard.
    Filters data based on the user's role (Admin vs Commercial).
    """
    
    # 1. Determine Scope based on permissions
    # If superuser or has specific permission, view ALL data.
    # Otherwise, view only data related to the user (Commercial scope).
    if user.is_superuser or user.has_permission('dashboard.view_all_stats'):
        sales_qs = CreditSale.objects.all()
        debts_qs = Debt.objects.all()
        recoveries_qs = Recovery.objects.all()
    else:
        # Commercial Scope
        # Sales: Owned directly OR in their Portfolio
        sales_qs = CreditSale.objects.filter(
            Q(commercial=user) | Q(portfolio__commercial=user)
        ).distinct()
        
        # Debts: Linked to the visible sales
        debts_qs = Debt.objects.filter(sale__in=sales_qs)
        
        # Recoveries: Linked to the visible debts
        recoveries_qs = Recovery.objects.filter(term__debt__in=debts_qs)

    # 2. Aggregate Sales Data
    sales_metrics = sales_qs.aggregate(
        total_volume=Coalesce(Sum('total_amount'), 0.0),
        total_count=Count('id'),
        approved_count=Count('id', filter=Q(status=CreditSaleStatus.APPROVED))
    )

    # 3. Aggregate Debt Data
    debt_metrics = debts_qs.aggregate(
        total_initial=Coalesce(Sum('init_amount'), 0.0),
        total_balance=Coalesce(Sum('balance'), 0.0),
        overdue_count=Count('id', filter=Q(debt_status=DebtStatus.OVERDUE))
    )

    # 4. Aggregate Recovery Data
    recovery_metrics = recoveries_qs.aggregate(
        total_collected=Coalesce(Sum('amount'), 0.0)
    )

    # 5. Calculate Ratios & Formatting
    total_initial_debt = debt_metrics['total_initial']
    total_collected = recovery_metrics['total_collected']
    
    recovery_rate = 0.0
    if total_initial_debt > 0:
        recovery_rate = (float(total_collected) / float(total_initial_debt)) * 100

    # 6. Construct Response Dictionary
    return {
        "sales": sales_metrics,
        "debts": debt_metrics,
        "recoveries": {
            "total_collected": total_collected,
            "recovery_rate": round(recovery_rate, 2)
        }
    }

def calculate_stats(queryset, aggregates):
    """
    Generic function to calculate aggregates on a queryset.
    """
    if not aggregates:
        return {}
    return queryset.aggregate(**aggregates)

def calculate_timeline(queryset, date_field, amount_field, alias='total_amount'):
    """
    Generic function to generate a monthly timeline.
    """
    return (
        queryset
        .annotate(month=TruncMonth(date_field))
        .values('month')
        .annotate(**{alias: Coalesce(Sum(amount_field), 0.0)})
        .order_by('month')
    )