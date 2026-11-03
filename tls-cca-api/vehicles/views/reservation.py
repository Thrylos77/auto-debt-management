"""Reservation read API; lifecycle mutations are vehicle-specific actions."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from rbac.policies.permission_policy import AutoPermissionMixin
from vehicles.filters import VehicleReservationFilter
from vehicles.models import VehicleReservation
from vehicles.serializers import VehicleReservationSerializer


@extend_schema(tags=["Vehicle Reservations"])
class VehicleReservationViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    resource = "reservation"
    serializer_class = VehicleReservationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = VehicleReservationFilter
    ordering_fields = ["reserved_at", "expires_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VehicleReservation.objects.none()
        return VehicleReservation.objects.select_related(
            "vehicle",
            "customer",
            "reserved_by",
            "released_by",
        ).all()
