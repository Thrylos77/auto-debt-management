"""Catalogue API endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from rbac.policies.permission_policy import AutoPermissionMixin
from vehicles.models import VehicleBrand, VehicleCategory, VehicleModel, VehicleVariant
from vehicles.serializers import (
    VehicleBrandSerializer,
    VehicleCategorySerializer,
    VehicleModelSerializer,
    VehicleVariantSerializer,
)


class CatalogueBaseViewSet(AutoPermissionMixin, viewsets.GenericViewSet):
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    permission_code_map = {}
    resource = "vehicle"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset


@extend_schema(tags=["Vehicle Catalogue"])
class VehicleCategoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, CatalogueBaseViewSet):
    queryset = VehicleCategory.objects.select_related("parent").all()
    serializer_class = VehicleCategorySerializer
    ordering_fields = ["name", "sort_order"]


@extend_schema(tags=["Vehicle Catalogue"])
class VehicleBrandViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, CatalogueBaseViewSet):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer
    ordering_fields = ["name"]


@extend_schema(tags=["Vehicle Catalogue"])
class VehicleModelViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, CatalogueBaseViewSet):
    queryset = VehicleModel.objects.select_related("brand", "category").all()
    serializer_class = VehicleModelSerializer
    ordering_fields = ["name", "brand__name"]
    filterset_fields = ["brand", "category", "is_active"]


@extend_schema(tags=["Vehicle Catalogue"])
class VehicleVariantViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, CatalogueBaseViewSet):
    queryset = VehicleVariant.objects.select_related("model__brand", "model").all()
    serializer_class = VehicleVariantSerializer
    ordering_fields = ["name", "model__name"]
    filterset_fields = ["model", "model__brand", "fuel_type", "transmission", "is_active"]
