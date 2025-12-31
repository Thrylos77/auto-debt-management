"""crm/tests/test_views.py"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from crm.models import Customer, PhysicalPersonDetail

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