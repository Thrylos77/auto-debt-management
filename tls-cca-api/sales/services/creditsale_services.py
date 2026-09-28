""" sales/services/creditsale_services.py """

from core.events import credit_sale_status_changed
from rbac.services.permission_resolver import PermissionResolver

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from sales.models import CreditSale, CreditSaleStatus
from receivables.models import Debt, DebtStatus
from receivables.services import term_services
from sales.policies.credit_sale_policy import CreditSalePolicy

def update_credit_sale_status(sale, new_status, user=None):
    """
    Updates the status of a CreditSale.
    If the status becomes APPROVED, automatically creates the associated Debt.

    Enforces a segregation-of-duties rule: the commercial who owns the sale
    cannot approve or reject their own sale (unless the actor is a superuser).
    Cancelling one's own sale remains allowed.
    """
    actor = user if user is not None else None
    if actor is not None and not CreditSalePolicy.can_change_status(
        actor,
        sale,
        new_status,
    ):
        raise PermissionDenied(
            _("You do not have permission to change this sale status."),
        )

    # If transitioning to APPROVED, create the Debt if it doesn't exist
    if new_status == CreditSaleStatus.APPROVED and sale.status != CreditSaleStatus.APPROVED:
        if not Debt.objects.filter(sale=sale).exists():
            debt_amount = sale.total_amount - sale.deposit
            with transaction.atomic():
                debt = Debt.objects.create(
                    sale=sale,
                    init_amount=debt_amount,
                    balance=debt_amount,
                    debt_status=DebtStatus.NOT_STARTED,
                    regulation_mode="UNDEFINED",  # Placeholder, needs to be defined later
                    month_duration=sale.month_duration,
                )
                # Automatically generate the payment schedule (Terms)
                monthly_payment = term_services.generate_terms_for_debt(debt, debt_amount)
                if monthly_payment != debt.monthly_payment:
                    debt.monthly_payment = monthly_payment
                    debt.save(update_fields=['monthly_payment'])

    previous_status = sale.status
    sale.status = new_status
    sale.save()
    if previous_status != new_status:
        credit_sale_status_changed.send(
            sender=CreditSale,
            sale=sale,
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
        )
    return sale

def get_sales_for_user(user):
    """
    Returns sales based on user role:
    - Admin/Superuser: All sales
    - Commercial: Sales where they are the commercial OR assigned via portfolio
    """
    if user.is_superuser or PermissionResolver.has(user, 'creditsale.list_all'):
        return CreditSale.objects.all()
    
    # For commercials: direct sales OR sales via their active portfolio
    return CreditSale.objects.filter(
        Q(commercial=user) | Q(portfolio__commercial=user)
    ).distinct()