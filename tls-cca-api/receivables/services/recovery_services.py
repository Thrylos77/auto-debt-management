from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError
from django.utils import timezone

from receivables.models import ( 
        Recovery, Term, Debt, 
        TermStatus, DebtStatus
    )
from crm.models import Portfolio

def create_recovery(commercial, term, amount, payment_mode, receipt=None):
    """
    Creates a recovery record and updates the related term and debt balances
    within a single atomic transaction.
    """
    if amount <= 0:
        raise ValidationError("Recovery amount must be positive.")

    # Ensure all database operations succeed or fail together
    with transaction.atomic():
        # 1. Create the recovery record
        recovery = Recovery.objects.create(
            commercial=commercial,
            term=term,
            amount=amount,
            payment_mode=payment_mode,
            receipt=receipt
        )

        # 2. Update the paid amount on the related term
        Term.objects.filter(pk=term.id).update(pay_amount=F('pay_amount') + amount)

        # 3. Re-fetch the debt to get its portfolio
        debt = Debt.objects.select_related('sale__portfolio').get(pk=term.debt_id)

        # 4. Subtract the amount from the total debt balance
        debt.balance = F('balance') - amount
        debt.save(update_fields=['balance'])
        debt.refresh_from_db() # Get the updated balance value

        # 5. Subtract the amount from the portfolio balance, if it exists
        if debt.sale and debt.sale.portfolio:
            Portfolio.objects.filter(pk=debt.sale.portfolio.id).update(balance=F('balance') - amount)

        # 6. Re-fetch the term to check its updated state
        updated_term = Term.objects.select_for_update().get(pk=term.id)

        # 7. Update term status
        if updated_term.pay_amount >= updated_term.except_amount:
            # Fully Paid
            if updated_term.term_status != TermStatus.PAID:
                updated_term.term_status = TermStatus.PAID
                updated_term.payment_date = timezone.now()
                updated_term.save(update_fields=['term_status', 'payment_date'])
        elif updated_term.pay_amount > 0:
            # Partially Paid
            today = timezone.now().date()
            new_status = TermStatus.PARTIALLY_PAID
            
            # If the term date has passed, it's partially overdue, not just partially paid
            if updated_term.term_date and updated_term.term_date < today:
                new_status = TermStatus.PARTIALLY_OVERDUE
            
            if updated_term.term_status != new_status:
                updated_term.term_status = new_status
                updated_term.save(update_fields=['term_status'])

        # 8. Update debt status if fully paid
        if debt.balance <= 0 and debt.debt_status != DebtStatus.PAID:
            debt.debt_status = DebtStatus.PAID
            debt.close_date = timezone.now().date() # Use .date() for DateField
            debt.save(update_fields=['debt_status', 'close_date'])
    return recovery