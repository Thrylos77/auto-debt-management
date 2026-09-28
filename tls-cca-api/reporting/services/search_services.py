"""Federated reporting/search services."""

from django.db.models import Q

from crm.models import Customer
from rbac.services.permission_resolver import PermissionResolver
from receivables.models import Debt
from sales.models import CreditSale


def search_global(user, query):
    """Search customers, credit sales and debts within the user's scope."""

    results = {
        "sales": [],
        "debts": [],
        "customers": [],
    }

    if not query or len(query) < 2:
        return results

    has_global_view = user.is_superuser or PermissionResolver.has(
        user,
        "dashboard.view_all_stats",
    )

    if has_global_view:
        sales_qs = CreditSale.objects.all()
    else:
        sales_qs = CreditSale.objects.filter(
            Q(commercial=user) | Q(portfolio__commercial=user)
        ).distinct()

    sales_hits = sales_qs.filter(
        Q(customer__physical_detail__first_name__icontains=query)
        | Q(customer__physical_detail__last_name__icontains=query)
        | Q(customer__moral_detail__business_name__icontains=query)
        | Q(customer__email__icontains=query)
    ).select_related(
        "customer",
        "customer__physical_detail",
        "customer__moral_detail",
        "commercial",
    )[:5]

    results["sales"] = [
        {
            "id": sale.id,
            "title": f"Vente #{sale.id} - {sale.customer.display_name}",
            "subtitle": f"Montant: {sale.total_amount}",
            "type": "sale",
            "url": f"/sales/creditsales/{sale.id}/",
        }
        for sale in sales_hits
    ]

    if has_global_view:
        debts_qs = Debt.objects.all()
    else:
        debts_qs = Debt.objects.filter(sale__in=sales_qs)

    debts_hits = debts_qs.filter(
        Q(sale__customer__physical_detail__first_name__icontains=query)
        | Q(sale__customer__physical_detail__last_name__icontains=query)
        | Q(sale__customer__moral_detail__business_name__icontains=query)
        | Q(sale__customer__email__icontains=query)
    ).select_related(
        "sale",
        "sale__customer",
        "sale__customer__physical_detail",
        "sale__customer__moral_detail",
    )[:5]

    results["debts"] = [
        {
            "id": debt.id,
            "title": f"Dette #{debt.id} - {debt.sale.customer.display_name}",
            "subtitle": f"Reste: {debt.balance}",
            "type": "debt",
            "status": debt.debt_status,
            "url": f"/receivables/debts/{debt.id}/",
        }
        for debt in debts_hits
    ]

    if user.is_superuser or PermissionResolver.has(user, "customer.list_all"):
        customers_qs = Customer.objects.all()
    elif PermissionResolver.has(user, "customer.list"):
        customers_qs = Customer.objects.filter(
            portfolio__commercial=user,
        )
    else:
        customers_qs = Customer.objects.none()

    customer_hits = customers_qs.filter(
        Q(physical_detail__first_name__icontains=query)
        | Q(physical_detail__last_name__icontains=query)
        | Q(moral_detail__business_name__icontains=query)
        | Q(email__icontains=query)
    ).select_related(
        "physical_detail",
        "moral_detail",
    )[:5]

    results["customers"] = [
        {
            "id": customer.id,
            "title": customer.display_name,
            "subtitle": customer.email or customer.phone,
            "type": "customer",
            "url": f"/crm/customers/{customer.id}/",
        }
        for customer in customer_hits
    ]

    return results
