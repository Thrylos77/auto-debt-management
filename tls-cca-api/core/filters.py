from django_filters import rest_framework as filters

class BaseDateRangeFilter(filters.FilterSet):
    """
    Base filter to handle date ranges (min_date, max_date).
    The child class must define 'date_field' in its Meta class.
    """
    min_date = filters.DateFilter(method='filter_min_date')
    max_date = filters.DateFilter(method='filter_max_date')

    def get_date_field(self):
        if hasattr(self.Meta, 'date_field'):
            return self.Meta.date_field
        raise NotImplementedError("The Meta class must define 'date_field' to use BaseDateRangeFilter.")

    def filter_min_date(self, queryset, name, value):
        field = self.get_date_field()
        return queryset.filter(**{f"{field}__gte": value})

    def filter_max_date(self, queryset, name, value):
        field = self.get_date_field()
        return queryset.filter(**{f"{field}__lte": value})