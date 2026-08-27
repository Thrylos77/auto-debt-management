from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from sales.models import CreditSale
from receivables.models import Debt, Recovery

def get_global_stats(user):
    """
    Calculates statistics based on the user's scope:
    - Superusers/users with 'dashboard.view_all_stats' see everything.
    - Other users (commercials) see only their sales, debts, and recoveries.
    """
    has_global_view = user.is_superuser or user.has_permission('dashboard.view_all_stats')

    if has_global_view:
        sales_qs = CreditSale.objects.all()
        debts_qs = Debt.objects.all()
        recoveries_qs = Recovery.objects.all()
    else:
        # Commercial scope: sales directly owned or in portfolios assigned to them
        sales_qs = CreditSale.objects.filter(
            Q(commercial=user) | Q(portfolio__commercial=user)
        ).distinct()
        
        # Debts linked to the visible sales
        debts_qs = Debt.objects.filter(sale__in=sales_qs)
        
        # Recoveries linked to visible terms
        recoveries_qs = Recovery.objects.filter(term__debt__in=debts_qs)

    sales_agg = sales_qs.aggregate(total=Coalesce(Sum('total_amount'), 0.0))
    debt_agg = debts_qs.aggregate(
        total_init=Coalesce(Sum('init_amount'), 0.0),
        total_balance=Coalesce(Sum('balance'), 0.0),
        active_count=Count('id', filter=Q(balance__gt=0))
    )
    recovery_agg = recoveries_qs.aggregate(total=Coalesce(Sum('amount'), 0.0))

    total_sales = sales_agg['total']
    total_init = debt_agg['total_init']
    total_balance = debt_agg['total_balance']
    total_recovered = recovery_agg['total']

    recovery_rate = 0.0
    if total_init > 0:
        recovery_rate = (float(total_recovered) / float(total_init)) * 100

    return {
        "total_sales": float(total_sales),
        "total_debt_initial": float(total_init),
        "total_debt_balance": float(total_balance),
        "total_recovered": float(total_recovered),
        "recovery_rate": round(recovery_rate, 2),
        "active_debtors_count": debt_agg['active_count']
    }
