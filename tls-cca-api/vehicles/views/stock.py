"""Read/manage stock locations and movement history."""

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter

from rbac.policies.permission_policy import AutoPermissionMixin
from vehicles.filters import StockLocationFilter, StockMovementFilter
from vehicles.models import StockLocation, StockMovement
from vehicles.serializers import StockLocationSerializer, StockMovementSerializer


@extend_schema(tags=["Vehicle Stock"])
class StockLocationViewSet(
    AutoPermissionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    resource = "stock"
    serializer_class = StockLocationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = StockLocationFilter
    ordering_fields = ["name", "code"]
    permission_code_map = {
        "list": "location.list",
        "retrieve": "location.list",
        "create": "location.manage",
        "update": "location.manage",
        "partial_update": "location.manage",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StockLocation.objects.none()
        return StockLocation.objects.annotate(
            vehicle_count=Count("current_vehicle_units")
        )


@extend_schema(tags=["Vehicle Stock"])
class StockMovementViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    resource = "stock"
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = StockMovementFilter
    ordering_fields = ["occurred_at"]
    permission_code_map = {
        "list": "view",
        "retrieve": "view",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StockMovement.objects.none()
        return StockMovement.objects.select_related(
            "vehicle",
            "from_location",
            "to_location",
            "performed_by",
        ).all()
