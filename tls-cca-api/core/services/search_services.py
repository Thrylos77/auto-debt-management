from django.db.models import Q
from sales.models import CreditSale
from receivables.models import Debt
from crm.models import Customer

def search_global(user, query):
    """
    Performs a federated search across multiple models (Sales, Debts).
    Respects the user's scope (RBAC).
    """
    results = {
        "sales": [],
        "debts": [],
        "customers": []
    }

    if not query or len(query) < 2:
        return results

    # --- 1. Search Scope Definition ---
    # We reuse the logic from stats_services to ensure consistency
    has_global_view = user.is_superuser or user.has_permission('dashboard.view_all_stats')

    # --- 2. Search in Credit Sales ---
    if has_global_view:
        sales_qs = CreditSale.objects.all()
    else:
        sales_qs = CreditSale.objects.filter(
            Q(commercial=user) | Q(portfolio__commercial=user)
        ).distinct()

    # Filter by query (Code, or linked Customer Name)
    # Adaptez 'code' et 'customer__name' selon vos vrais noms de champs
    sales_hits = sales_qs.filter(
        Q(code__icontains=query) 
        # | Q(customer__name__icontains=query) 
    ).select_related('commercial')[:5] # Limit to 5 results for performance

    results["sales"] = [
        {
            "id": sale.id,
            "title": f"Vente {sale.code}",
            "subtitle": f"Montant: {sale.total_amount}",
            "type": "sale",
            "url": f"/sales/creditsales/{sale.id}/"
        }
        for sale in sales_hits
    ]

    # --- 3. Search in Debts ---
    if has_global_view:
        debts_qs = Debt.objects.all()
    else:
        # Debts linked to visible sales
        debts_qs = Debt.objects.filter(sale__in=sales_qs)

    # Filter by query (Code, Reference)
    debts_hits = debts_qs.filter(
        Q(sale__code__icontains=query)
        # | Q(sale__customer__name__icontains=query)
    )[:5]

    results["debts"] = [
        {
            "id": debt.id,
            "title": f"Dette {debt.code}",
            "subtitle": f"Reste: {debt.balance}",
            "type": "debt",
            "status": debt.debt_status,
            "url": f"/receivables/debts/{debt.id}/"
        }
        for debt in debts_hits
    ]

    # --- 4. Search in Customers ---
    # RBAC: Admin/Consultant sees all, Commercial sees own
    if user.is_superuser or user.has_permission('customer.list_all'):
        customers_qs = Customer.objects.all()
    elif user.has_permission('customer.list'):
        customers_qs = Customer.objects.filter(commercial=user)
    else:
        customers_qs = Customer.objects.none()

    # Filter by query (Name, Email)
    customer_hits = customers_qs.filter(
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    )[:5]

    results["customers"] = [
        {
            "id": customer.id,
            "title": f"{customer.first_name} {customer.last_name}",
            "subtitle": customer.email,
            "type": "customer",
            "url": f"/crm/customers/{customer.id}/"
        }
        for customer in customer_hits
    ]

    return results