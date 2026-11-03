"""API filters for the vehicles and inventory domain."""

from django.db.models import Q
from django_filters import rest_framework as filters

from .models import StockLocation, StockMovement, VehicleReservation, VehicleUnit


class VehicleUnitFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    price_min = filters.NumberFilter(field_name="current_price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="current_price", lookup_expr="lte")
    brand = filters.NumberFilter(field_name="variant__model__brand_id")
    model = filters.NumberFilter(field_name="variant__model_id")
    variant = filters.NumberFilter(field_name="variant_id")
    category = filters.NumberFilter(field_name="variant__model__category_id")
    location = filters.NumberFilter(field_name="current_location_id")
    vin_or_chassis = filters.CharFilter(method="filter_vin_or_chassis")

    class Meta:
        model = VehicleUnit
        fields = [
            "stock_reference",
            "color",
            "condition",
            "status",
            "manufacture_year",
            "brand",
            "model",
            "variant",
            "category",
            "location",
            "price_min",
            "price_max",
            "vin_or_chassis",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(stock_reference__icontains=value)
            | Q(vin__icontains=value)
            | Q(chassis_number__icontains=value)
            | Q(variant__name__icontains=value)
            | Q(variant__model__name__icontains=value)
            | Q(variant__model__brand__name__icontains=value)
        ).distinct()

    def filter_vin_or_chassis(self, queryset, name, value):
        return queryset.filter(
            Q(vin__iexact=value) | Q(chassis_number__iexact=value)
        )


class StockLocationFilter(filters.FilterSet):
    class Meta:
        model = StockLocation
        fields = ["code", "type", "is_active"]


class StockMovementFilter(filters.FilterSet):
    class Meta:
        model = StockMovement
        fields = ["vehicle", "movement_type", "from_location", "to_location", "performed_by"]


class VehicleReservationFilter(filters.FilterSet):
    class Meta:
        model = VehicleReservation
        fields = ["vehicle", "customer", "reserved_by", "status"]
