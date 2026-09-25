""" receivables/services/term_services.py """

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from receivables.models import Term, TermStatus


def _term_dates(debt, count):
    """
    Returns the list of term due dates (``count`` entries).

    The due day is anchored on the sale's ``first_due_date`` when provided,
    otherwise on the debt ``start_date`` (the first term is then due one month
    after that date). When a month is shorter than the anchor day, the term
    falls on the last day of that month (e.g. 31 Jan -> 28/29 Feb -> 31 Mar).
    """
    first_due = getattr(debt.sale, 'first_due_date', None)
    if first_due:
        anchor = first_due
        first_term = first_due
    else:
        start = debt.start_date or timezone.localdate()
        anchor = start
        first_term = start + relativedelta(months=1)

    dates = []
    for index in range(count):
        target = first_term + relativedelta(months=index)
        last_day = monthrange(target.year, target.month)[1]
        dates.append(date(target.year, target.month, min(anchor.day, last_day)))
    return dates


def generate_terms_for_debt(debt, amount):
    """
    Generates the payment schedule (Terms) for a Debt by splitting ``amount``
    into ``debt.month_duration`` monthly installments.

    The last term absorbs the rounding remainder so that the sum of all
    ``except_amount`` equals ``amount`` exactly.

    Returns the rounded monthly installment amount (to be stored on
    ``Debt.monthly_payment``).
    """
    duration = max(int(debt.month_duration or 1), 1)
    monthly_amount = (Decimal(amount) / Decimal(duration)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    terms = []
    remaining = Decimal(amount)
    for index, term_date in enumerate(_term_dates(debt, duration)):
        except_amount = monthly_amount
        if index == duration - 1:
            # Last term absorbs the rounding remainder to reach the exact total
            except_amount = remaining.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        terms.append(
            Term(
                debt=debt,
                term_date=term_date,
                except_amount=except_amount,
                pay_amount=Decimal('0.00'),
                term_status=TermStatus.UNPAID,
            )
        )
        remaining -= except_amount

    Term.objects.bulk_create(terms)
    return monthly_amount
