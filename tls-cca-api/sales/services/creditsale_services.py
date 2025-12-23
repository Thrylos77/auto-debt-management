from sales.models import CreditSaleStatus
from receivables.models import Debt

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
                regulation_mode="UNDEFINED" # Placeholder, needs to be defined later
            )

    sale.status = new_status
    sale.save()
    return sale