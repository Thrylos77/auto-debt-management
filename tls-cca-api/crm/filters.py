""" crm/filters.py """

import django_filters
from django.contrib.auth import get_user_model
from .models import Customer

User = get_user_model()

class CustomerFilter(django_filters.FilterSet):
    """
    FilterSet for the Customer model.

    Allows filtering by:
    - customer_type (exact match)
    - is_active (exact match)
    - commercial (user responsible for the portfolio)
    """

    # Map the filter directly to the portfolio relation.  Besides being
    # simpler than a custom method, this lets drf-spectacular infer the
    # parameter as a user primary key instead of falling back to a string.
    commercial = django_filters.ModelChoiceFilter(
        field_name="portfolio__commercial",
        queryset=User.objects.all(),
        label="Commercial",
    )

    class Meta:
        model = Customer
        fields = {
            'customer_type': ['exact'],
            'is_active': ['exact'],
        }
