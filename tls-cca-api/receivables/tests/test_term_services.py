"""receivables/tests/test_term_services.py"""
import pytest
from datetime import date
from decimal import Decimal

from crm.models import Customer, Portfolio
from receivables.models import Debt, TermStatus
from receivables.services import term_services
from sales.models import CreditSale
from users.models import User


@pytest.fixture
def debt_factory(db):
    """Factory creating a CreditSale + its Debt and returning the Debt."""

    def _create(month_duration=1, first_due_date=None, total_amount=Decimal('900.00'),
                deposit=Decimal('0.00'), start_date=date(2025, 1, 15)):
        seed = abs(hash((month_duration, first_due_date, start_date, total_amount))) % 10 ** 8
        commercial = User.objects.create_user(
            username=f"term_user_{seed}",
            password='pw',
            is_active=True,
        )
        customer = Customer.objects.create(
            phone='0600000000',
            email=f"term_customer_{seed}@example.com",
        )
        portfolio = Portfolio.objects.create(
            ref=f"PF_TERM_{seed % 10 ** 5}",
            commercial=commercial,
        )
        sale = CreditSale.objects.create(
            customer=customer,
            commercial=commercial,
            portfolio=portfolio,
            total_amount=total_amount,
            deposit=deposit,
            month_duration=month_duration,
            first_due_date=first_due_date,
        )
        init = total_amount - deposit
        return Debt.objects.create(
            sale=sale,
            init_amount=init,
            balance=init,
            start_date=start_date,
            month_duration=month_duration,
            regulation_mode='MONTHLY',
        )

    return _create


@pytest.mark.django_db
def test_generates_even_monthly_terms(debt_factory):
    """A divisible amount is split evenly and terms are due at month intervals."""
    debt = debt_factory(month_duration=12, total_amount=Decimal('900.00'))

    monthly = term_services.generate_terms_for_debt(debt, debt.init_amount)

    assert monthly == Decimal('75.00')
    terms = list(debt.terms.order_by('term_date'))
    assert len(terms) == 12
    assert [t.except_amount for t in terms] == [Decimal('75.00')] * 12
    assert all(t.pay_amount == Decimal('0.00') for t in terms)
    assert all(t.term_status == TermStatus.UNPAID for t in terms)
    # first term = start_date + 1 month, then consecutive months
    assert terms[0].term_date == date(2025, 2, 15)
    assert terms[-1].term_date == date(2026, 1, 15)


@pytest.mark.django_db
def test_last_term_absorbs_rounding_remainder(debt_factory):
    """When the amount is not divisible, the last term absorbs the remainder."""
    debt = debt_factory(month_duration=3, total_amount=Decimal('100.00'))

    monthly = term_services.generate_terms_for_debt(debt, debt.init_amount)

    assert monthly == Decimal('33.33')
    terms = list(debt.terms.order_by('term_date'))
    assert [t.except_amount for t in terms] == [
        Decimal('33.33'), Decimal('33.33'), Decimal('33.34')
    ]
    assert sum((t.except_amount for t in terms), Decimal('0.00')) == debt.init_amount


@pytest.mark.django_db
def test_first_due_date_is_used_when_provided(debt_factory):
    """The sale's first_due_date is used as the first term date when set."""
    debt = debt_factory(month_duration=3, first_due_date=date(2025, 3, 10))

    term_services.generate_terms_for_debt(debt, debt.init_amount)

    terms = list(debt.terms.order_by('term_date'))
    assert [t.term_date for t in terms] == [
        date(2025, 3, 10), date(2025, 4, 10), date(2025, 5, 10)
    ]


@pytest.mark.django_db
def test_month_end_rollover(debt_factory):
    """31 Jan + 1 month rolls over correctly to the last day of Feb."""
    debt = debt_factory(month_duration=2, total_amount=Decimal('200.00'),
                        start_date=date(2025, 1, 31))

    term_services.generate_terms_for_debt(debt, debt.init_amount)

    terms = list(debt.terms.order_by('term_date'))
    assert [t.term_date for t in terms] == [date(2025, 2, 28), date(2025, 3, 31)]


@pytest.mark.django_db
def test_single_term_equals_full_amount(debt_factory):
    """With month_duration=1 the single term covers the whole debt amount."""
    debt = debt_factory(month_duration=1, total_amount=Decimal('800.00'),
                        deposit=Decimal('200.00'))

    monthly = term_services.generate_terms_for_debt(debt, debt.init_amount)

    assert debt.init_amount == Decimal('600.00')
    assert monthly == Decimal('600.00')
    terms = list(debt.terms.all())
    assert len(terms) == 1
    assert terms[0].except_amount == Decimal('600.00')