import pytest
from crm.models import Customer, PhysicalPersonDetail, MoralPersonDetail

@pytest.mark.django_db
def test_customer_physical_person_display_name():
    """
    Test the display_name property for a physical person customer.
    """
    customer = Customer.objects.create(
        phone='1234567890',
        email='physical@example.com'
    )
    PhysicalPersonDetail.objects.create(
        customer=customer,
        first_name='John',
        last_name='Doe'
    )
    assert customer.display_name == "John Doe"

@pytest.mark.django_db
def test_customer_moral_person_display_name():
    """
    Test the display_name property for a moral person customer.
    """
    customer = Customer.objects.create(
        customer_type=Customer.TYPE_MORAL,
        phone='0987654321',
        email='moral@example.com'
    )
    MoralPersonDetail.objects.create(
        customer=customer,
        business_name='Test Corp'
    )
    assert customer.display_name == "Test Corp"

@pytest.mark.django_db
def test_customer_display_name_fallbacks():
    """
    Test the display_name property fallbacks when no detail is provided.
    """
    # Test fallback to email
    customer_email = Customer.objects.create(
        phone='111222333',
        email='fallback@example.com'
    )
    assert customer_email.display_name == 'fallback@example.com'

    # Test fallback to phone
    customer_phone = Customer.objects.create(
        phone='444555666'
    )
    assert customer_phone.display_name == '444555666'
