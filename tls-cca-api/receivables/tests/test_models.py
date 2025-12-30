import pytest
from decimal import Decimal
from receivables.models import Debt
from sales.models import CreditSale
from crm.models import Customer
from users.models import User

@pytest.mark.django_db
def test_debt_creation():
    """
    Test that a Debt can be created and is correctly linked to a CreditSale.
    """
    # 1. Create prerequisites
    commercial = User.objects.create_user(
        username='commercial', 
        password='password',
        first_name='Comm',
        last_name='Ercial'
    )
    customer = Customer.objects.create(
        phone='123456789',
        email='customer@sale.com'
    )
    
    # 2. Create a CreditSale
    sale = CreditSale.objects.create(
        customer=customer,
        commercial=commercial,
        total_amount=Decimal('1000.00'),
        deposit=Decimal('100.00')
    )

    # 3. Create a Debt
    # This would typically be done by a signal or a service, 
    # but we test the model creation directly here.
    debt = Debt.objects.create(
        sale=sale,
        init_amount=sale.total_amount - sale.deposit,
        balance=sale.total_amount - sale.deposit
    )

    # 4. Assertions
    assert debt.sale == sale
    assert debt.init_amount == Decimal('900.00')
    assert debt.balance == Decimal('900.00')
    assert str(debt) == f"Debt for sale #{sale.pk} (900.00/900.00)"
    
    # Check reverse relationship
    assert hasattr(sale, 'debts')
    assert sale.debts == debt
