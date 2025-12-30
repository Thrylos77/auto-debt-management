"""sales/tests/test_views.py"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from sales.models import CreditSale
from crm.models import Portfolio

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestCreditSaleViews:
    def test_list_sales(self, api_client, new_user, new_customer):
        """Test listing credit sales."""
        # Create a sale manually first
        portfolio = Portfolio.objects.create(ref='PF_TEST_VIEW', commercial=new_user)
        CreditSale.objects.create(
            customer=new_customer,
            commercial=new_user,
            portfolio=portfolio,
            total_amount=Decimal('1000.00')
        )
        
        url = reverse('creditsale-list')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_create_sale(self, api_client, new_user, new_customer):
        """Test creating a credit sale via API."""
        # Ensure the user has a portfolio or the system assigns one
        Portfolio.objects.create(ref='PF_DEFAULT', commercial=new_user)
        
        url = reverse('creditsale-list')
        api_client.force_authenticate(user=new_user)
        data = {
            'customer': new_customer.pk,
            'total_amount': '5000.00',
            'deposit': '500.00'
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert CreditSale.objects.count() >= 1