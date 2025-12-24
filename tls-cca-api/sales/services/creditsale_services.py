from django.db.models import Q
from sales.models import CreditSale, CreditSaleStatus
from receivables.models import Debt, DebtStatus

def update_credit_sale_status(sale, new_status):
    """
    Updates the status of a CreditSale.
    If the status becomes APPROVED, automatically creates the associated Debt.
    """
    # If transitioning to APPROVED, create the Debt if it doesn't exist
    if new_status == CreditSaleStatus.APPROVED and sale.status != CreditSaleStatus.APPROVED:
        if not Debt.objects.filter(sale=sale).exists():
            debt_amount = sale.total_amount - sale.deposit
            Debt.objects.create(
                sale=sale,
                init_amount=debt_amount,
                balance=debt_amount,
                status=DebtStatus.NOT_STARTED,
                regulation_mode="UNDEFINED" # Placeholder, needs to be defined later
            )

    sale.status = new_status
    sale.save()
    return sale

def get_sales_for_user(user):
    """
    Returns sales based on user role:
    - Admin/Superuser: All sales
    - Commercial: Sales where they are the commercial OR assigned via portfolio
    """
    if user.is_superuser or user.has_permission('creditsale.list_all'):
        return CreditSale.objects.all()
    
    # For commercials: direct sales OR sales via their active portfolio
    return CreditSale.objects.filter(
        Q(commercial=user) | Q(portfolio__commercial=user)
    ).distinct()