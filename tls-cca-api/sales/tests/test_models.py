import pytest
from decimal import Decimal
from sales.models import CreditSale
from crm.models import Portfolio

@pytest.mark.django_db
def test_credit_sale_creation(new_user, new_customer):
    """
    Test that a CreditSale can be created.
    """
    portfolio = Portfolio.objects.create(ref='PF001', commercial=new_user)

    sale = CreditSale.objects.create(
        customer=new_customer,
        commercial=new_user,
        portfolio=portfolio,
        total_amount=Decimal('5000.00'),
        deposit=Decimal('500.00')
    )

    assert sale.customer == new_customer
    assert sale.commercial == new_user
    assert sale.portfolio == portfolio
    assert sale.total_amount == Decimal('5000.00')
    assert str(sale) == f"Sale #{sale.pk} - {new_customer.display_name} (5000.00)"


@pytest.mark.django_db
def test_credit_sale_default_portfolio_assignment(new_user, new_customer):
    """
    Test that a default portfolio is assigned to a sale if not specified.
    """
    # Create a portfolio and assign it to the commercial
    portfolio = Portfolio.objects.create(ref='PF002', commercial=new_user)
    
    # Create the sale *without* specifying the portfolio
    sale = CreditSale.objects.create(
        customer=new_customer,
        commercial=new_user,
        total_amount=Decimal('300.00')
    )
    
    # The save() method should have automatically assigned the portfolio
    assert sale.portfolio is not None
    assert sale.portfolio == portfolio
