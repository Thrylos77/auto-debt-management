"""receivables/tests/test_views.py"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from receivables.models import Debt
from sales.models import CreditSale
from crm.models import Portfolio

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestDebtViews:
    def test_list_debts(self, api_client, new_user, new_customer):
        """Test listing debts."""
        # Setup data
        portfolio = Portfolio.objects.create(ref='PF_DEBT_VIEW', commercial=new_user)
        sale = CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal('2000.00')
        )
        Debt.objects.create(
            sale=sale,
            init_amount=Decimal('2000.00'),
            balance=Decimal('2000.00')
        )

        url = reverse('debt-list')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_retrieve_debt(self, api_client, new_user, new_customer):
        """Test retrieving a specific debt."""
        portfolio = Portfolio.objects.create(ref='PF_DEBT_VIEW_2', commercial=new_user)
        sale = CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal('1000.00')
        )
        debt = Debt.objects.create(
            sale=sale,
            init_amount=Decimal('1000.00'),
            balance=Decimal('1000.00')
        )

        url = reverse('debt-detail', kwargs={'pk': debt.pk})
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert Decimal(response.data['balance']) == Decimal('1000.00')