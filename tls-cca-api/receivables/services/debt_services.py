from datetime import timedelta
from django.utils import timezone
from receivables.models import Debt, DebtStatus, Term, TermStatus

def update_financial_statuses():
    """
    Updates the statuses of Debts and Terms based on the current date.
    This function is intended to be called periodically (e.g., daily via a cron job).
    """
    today = timezone.now().date()

    # --- 1. TERMS STATUSES ---
    # UNPAID -> OVERDUE if the date has passed
    Term.objects.filter(
        term_status=TermStatus.UNPAID,
        term_date__lt=today
    ).update(term_status=TermStatus.OVERDUE)

    # PARTIALLY_PAID -> PARTIALLY_OVERDUE if the date has passed
    Term.objects.filter(
        term_status=TermStatus.PARTIALLY_PAID,
        term_date__lt=today
    ).update(term_status=TermStatus.PARTIALLY_OVERDUE)


    # --- 2. DEBTS STATUSES ---
    # NOT_STARTED -> ONGOING if start_date is reached
    Debt.objects.filter(
        debt_status=DebtStatus.NOT_STARTED,
        start_date__lte=today
    ).update(debt_status=DebtStatus.ONGOING)

    # ONGOING -> OVERDUE
    # Logic: If the theoretical deadline is passed and balance > 0.
    # Since close_date is used for "Date Paid", we calculate deadline = start_date + month_duration
    ongoing_debts = Debt.objects.filter(debt_status=DebtStatus.ONGOING)
    
    debts_to_update = []
    for debt in ongoing_debts:
        if debt.start_date:
            # Approximation: 30.44 days per month
            deadline = debt.start_date + timedelta(days=int(debt.month_duration * 30.44))
            if deadline < today and debt.balance > 0:
                debt.debt_status = DebtStatus.OVERDUE
                debts_to_update.append(debt)
    
    if debts_to_update:
        Debt.objects.bulk_update(debts_to_update, ['debt_status'])
    
    return len(debts_to_update)