"""Physical inventory API endpoints."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from rbac.policies.permission_policy import AutoPermissionMixin
from vehicles.models import InventorySession
from vehicles.serializers import (
    CreateInventorySessionSerializer,
    InventoryItemSerializer,
    InventorySessionDetailSerializer,
    InventorySessionSerializer,
    RecordInventoryItemSerializer,
)
from vehicles.services import (
    create_inventory_session,
    record_inventory_item,
    start_inventory,
    submit_inventory,
    validate_inventory,
)
from vehicles.views import run_service


@extend_schema(tags=["Vehicle Inventory"])
class InventorySessionViewSet(
    AutoPermissionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    resource = "inventory"
    serializer_class = InventorySessionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["location", "status", "started_by", "validated_by"]
    ordering_fields = ["created_at", "started_at", "reference"]
    permission_code_map = {
        "start": "create",
        "record": "record",
        "submit": "submit",
        "validate": "validate",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InventorySession.objects.none()
        return InventorySession.objects.select_related(
            "location",
            "started_by",
            "validated_by",
        ).all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return InventorySessionDetailSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = CreateInventorySessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = run_service(
            create_inventory_session,
            location=serializer.validated_data["location"],
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
            request=request,
        )
        return Response(
            InventorySessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses=InventorySessionDetailSerializer)
    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        session = self.get_object()
        updated = run_service(start_inventory, session=session, actor=request.user, request=request)
        return Response(InventorySessionDetailSerializer(updated).data)

    @extend_schema(request=RecordInventoryItemSerializer, responses={200: InventoryItemSerializer})
    @action(detail=True, methods=["post"], url_path="record")
    def record(self, request, pk=None):
        session = self.get_object()
        serializer = RecordInventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = run_service(
            record_inventory_item,
            session=session,
            actor=request.user,
            request=request,
            **serializer.validated_data,
        )
        return Response(InventoryItemSerializer(item).data)

    @extend_schema(responses=InventorySessionSerializer)
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        session = self.get_object()
        updated = run_service(submit_inventory, session=session, actor=request.user, request=request)
        return Response(InventorySessionSerializer(updated).data)

    @extend_schema(responses=InventorySessionDetailSerializer)
    @action(detail=True, methods=["post"], url_path="validate")
    def validate(self, request, pk=None):
        session = self.get_object()
        updated = run_service(validate_inventory, session=session, actor=request.user, request=request)
        return Response(InventorySessionDetailSerializer(updated).data)
