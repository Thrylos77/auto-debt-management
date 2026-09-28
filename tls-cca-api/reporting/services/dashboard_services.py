"""Dashboard aggregation services."""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from rbac.services.permission_resolver import PermissionResolver
from receivables.models import Debt, Recovery
from sales.models import CreditSale


def get_dashboard_stats(user=None):
    """Return dashboard KPIs within the actor's authorized data scope."""

    has_global_view = (
        user is None
        or user.is_superuser
        or PermissionResolver.has(user, "dashboard.view_all_stats")
    )

    if has_global_view:
        sales_qs = CreditSale.objects.all()
        debts_qs = Debt.objects.all()
        recoveries_qs = Recovery.objects.all()
    else:
        sales_qs = CreditSale.objects.filter(
            Q(commercial=user) | Q(portfolio__commercial=user)
        ).distinct()
        debts_qs = Debt.objects.filter(sale__in=sales_qs)
        recoveries_qs = Recovery.objects.filter(term__debt__in=debts_qs)

    sales_agg = sales_qs.aggregate(
        total=Coalesce(Sum("total_amount"), Decimal("0.00")),
    )
    debt_agg = debts_qs.aggregate(
        total_init=Coalesce(Sum("init_amount"), Decimal("0.00")),
        total_balance=Coalesce(Sum("balance"), Decimal("0.00")),
        active_count=Count("id", filter=Q(balance__gt=0)),
    )
    recovery_agg = recoveries_qs.aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00")),
    )

    total_sales = sales_agg["total"]
    total_init = debt_agg["total_init"]
    total_balance = debt_agg["total_balance"]
    total_recovered = recovery_agg["total"]

    recovery_rate = 0.0
    if total_init > 0:
        recovery_rate = (float(total_recovered) / float(total_init)) * 100

    return {
        "total_sales": float(total_sales),
        "total_debt_initial": float(total_init),
        "total_debt_balance": float(total_balance),
        "total_recovered": float(total_recovered),
        "recovery_rate": round(recovery_rate, 2),
        "active_debtors_count": debt_agg["active_count"],
    }

