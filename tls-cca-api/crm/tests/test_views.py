"""crm/tests/test_views.py"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from crm.models import Customer, PhysicalPersonDetail, PortfolioTransfer
from crm.services.portfolio_services import create_portfolio_for_commercial

User = get_user_model()

@pytest.fixture
def api_client():
    return  APIClient()

@pytest.mark.django_db
class TestCustomerViews:
    def test_list_customers(self, api_client, new_user):
        """Test listing customers for an authenticated user."""
        url = reverse('customer-list')
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_create_customer(self, api_client, new_user):
        """Test creating a new customer via API."""
        url = reverse('customer-list')
        api_client.force_authenticate(user=new_user)
        data = {
            'customer_type': 'physical',
            'email': 'newcustomer@example.com',
            'phone': '1234567890',
            'address': '123 Test Street',
            'physical_detail': {
                'first_name': 'John',
                'last_name': 'Doe',
                'birth_day': '1990-01-01',
                'birth_place': 'City',
                'id_document_type': 'Passport',
                'id_document_number': 'P12345678',
                'nationality': 'Country'
            }
        }
        response = api_client.post(url, data, format='json')
        print(response.data)
        assert response.status_code == 201
        assert Customer.objects.filter(email='newcustomer@example.com').exists()
        assert PhysicalPersonDetail.objects.filter(customer__email='newcustomer@example.com').exists()
 
    def test_retrieve_customer(self, api_client, new_user, new_customer):
        """Test retrieving a specific customer."""
        url = reverse('customer-detail', kwargs={'pk': new_customer.pk})
        api_client.force_authenticate(user=new_user)
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['email'] == new_customer.email


@pytest.mark.django_db
class TestPortfolioViews:
    @pytest.fixture
    def owner(self):
        return User.objects.create_user(
            username='owner', email='owner@example.com', password='x', is_active=True
        )

    @pytest.fixture
    def target(self):
        return User.objects.create_user(
            username='target', email='target@example.com', password='x', is_active=True
        )

    @pytest.fixture
    def portfolio(self, owner):
        return create_portfolio_for_commercial(owner)

    def test_assign_existing_portfolio(self, api_client, new_user, portfolio, target):
        api_client.force_authenticate(user=new_user)
        url = reverse('portfolio-assign', kwargs={'pk': portfolio.pk})
        response = api_client.post(url, {'commercial': target.id, 'reason': 'Reaffectation'}, format='json')
        assert response.status_code == 200
        assert response.data['commercial'] == target.id
        portfolio.refresh_from_db()
        assert portfolio.commercial_id == target.id
        assert PortfolioTransfer.objects.filter(
            portfolio=portfolio, to_commercial=target, reason='Reaffectation'
        ).exists()

    def test_assign_rejects_inactive_target(self, api_client, new_user, portfolio, target):
        target.is_active = False
        target.save()
        api_client.force_authenticate(user=new_user)
        url = reverse('portfolio-assign', kwargs={'pk': portfolio.pk})
        response = api_client.post(url, {'commercial': target.id}, format='json')
        assert response.status_code == 400

    def test_transfer_portfolio(self, api_client, new_user, portfolio, target):
        api_client.force_authenticate(user=new_user)
        url = reverse('portfolio-transfer', kwargs={'pk': portfolio.pk})
        response = api_client.post(url, {'to_commercial': target.id, 'reason': 'Depart'}, format='json')
        assert response.status_code == 200
        assert response.data['commercial'] == target.id
        assert PortfolioTransfer.objects.filter(
            portfolio=portfolio, to_commercial=target, reason='Depart'
        ).exists()

    def test_list_portfolio_transfers(self, api_client, new_user, portfolio, target):
        from crm.services.portfolio_services import assign_portfolio
        assign_portfolio(portfolio, target, transferred_by=new_user, reason='log')
        api_client.force_authenticate(user=new_user)
        url = reverse('portfolio-transfer-list')
        response = api_client.get(url)
        assert response.status_code == 200
        assert PortfolioTransfer.objects.count() >= 1
        assert any(t['portfolio'] == portfolio.id for t in response.data['results'])