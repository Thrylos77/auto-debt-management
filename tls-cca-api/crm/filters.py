# crm/filters.py
import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Customer

User = get_user_model()

class CustomerFilter(django_filters.FilterSet):
    """
    FilterSet for the Customer model.

    Allows filtering by:
    - customer_type (exact match)
    - is_active (exact match)
    - commercial (exact match on user ID)
    """
    portfolio__commercial = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(
            Q(groups__permissions__codename='customer.create') |
            Q(user_permissions__codename='customer.create') |
            Q(is_superuser=True)
        ).distinct(),
        field_name='portfolio__commercial',
        label="Commercial"
    )

    class Meta:
        model = Customer
        fields = {
            'customer_type': ['exact'],
            'is_active': ['exact'],
        }