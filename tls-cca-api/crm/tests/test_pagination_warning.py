import warnings
import pytest
from django.core.paginator import UnorderedObjectListWarning
from django.urls import reverse
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_customer_list_all_has_deterministic_order(new_user, new_customer):
    client = APIClient(); client.force_authenticate(user=new_user)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", UnorderedObjectListWarning)
        response = client.get(reverse("customer-list-all"))
    assert response.status_code == 200
    assert not [w for w in caught if issubclass(w.category, UnorderedObjectListWarning)]
