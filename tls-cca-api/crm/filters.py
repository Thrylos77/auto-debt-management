"""Customer API filters."""

import django_filters
from django.contrib.auth import get_user_model

from .models import Customer

User = get_user_model()


class CustomerFilter(django_filters.FilterSet):
    """Filter customers by type, compatibility activity and lifecycle status."""

    commercial = django_filters.ModelChoiceFilter(
        field_name="portfolio__commercial",
        queryset=User.objects.all(),
        label="Commercial",
    )
    neighborhood = django_filters.CharFilter(
        field_name="addresses__neighborhood",
        lookup_expr="iexact",
        distinct=True,
    )
    city = django_filters.CharFilter(
        field_name="addresses__city",
        lookup_expr="iexact",
        distinct=True,
    )
    country = django_filters.CharFilter(
        field_name="addresses__country",
        lookup_expr="iexact",
        distinct=True,
    )
    country_code = django_filters.CharFilter(
        field_name="addresses__country_code",
        lookup_expr="iexact",
        distinct=True,
    )

    class Meta:
        model = Customer
        fields = {
            "customer_type": ["exact"],
            "is_active": ["exact"],
            "lifecycle_status": ["exact"],
            "preferred_contact_channel": ["exact"],
        }
