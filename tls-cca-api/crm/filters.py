# crm/filters.py
import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Customer

User = get_user_model()

def commercial_queryset(request):
    return User.objects.filter(
        is_active=True,
    ).filter(
        Q(user_permissions__codename='customer.create') |
        Q(groups__group__permissions__codename='customer.create') |
        Q(is_superuser=True)
    ).distinct()


class CustomerFilter(django_filters.FilterSet):
    """
    FilterSet for the Customer model.

    Allows filtering by:
    - customer_type (exact match)
    - is_active (exact match)
    - commercial (user responsible for the portfolio)
    """

    commercial = django_filters.ModelChoiceFilter(
        method="filter_commercial",
        queryset=User.objects.all(),
        label="Commercial",
    )

    class Meta:
        model = Customer
        fields = {
            'customer_type': ['exact'],
            'is_active': ['exact'],
        }

    def filter_commercial(self, queryset, name, value):
        return queryset.filter(portfolio__commercial=value)