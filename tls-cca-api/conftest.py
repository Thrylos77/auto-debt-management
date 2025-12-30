"""conftest.py"""
import pytest
from django.contrib.auth import get_user_model
from crm.models import Customer
from faker import Faker

fake = Faker()

@pytest.fixture
def new_user(db):
    """
    Fixture to create a new user.
    """
    User = get_user_model()
    user = User.objects.create_user(
        username=fake.user_name(),
        email=fake.email(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        password='password123',
        is_superuser=True
    )
    return user

@pytest.fixture
def new_customer(db):
    """
    Fixture to create a new customer.
    """
    customer = Customer.objects.create(
        customer_type='physical',
        email=fake.email(),
        phone=fake.phone_number(),
        address=fake.address()
    )
    return customer