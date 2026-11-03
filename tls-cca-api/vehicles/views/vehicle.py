"""Vehicle unit API endpoints and dedicated stock-control actions."""

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from rbac.policies.permission_policy import AutoPermissionMixin
from vehicles.filters import VehicleUnitFilter
from vehicles.models import VehicleUnit
from vehicles.serializers import (
    ChangeVehiclePriceSerializer,
    CreateVehicleReservationSerializer,
    ReceiveVehicleSerializer,
    ReleaseReservationSerializer,
    TransferVehicleSerializer,
    VehicleImageSerializer,
    VehiclePriceHistorySerializer,
    VehicleReservationSerializer,
    VehicleStatusReasonSerializer,
    VehicleUnitSerializer,
)
from vehicles.services import (
    add_vehicle_image,
    block_vehicle,
    change_vehicle_price,
    create_vehicle_unit,
    generate_vehicle_qr,
    receive_vehicle,
    release_reservation,
    reserve_vehicle,
    transfer_vehicle,
    unblock_vehicle,
    update_vehicle_unit,
)
from vehicles.views import run_service
from vehicles.models import VehicleReservation


@extend_schema(tags=["Vehicles"])
class VehicleUnitViewSet(
    AutoPermissionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    resource = "vehicle"
    serializer_class = VehicleUnitSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VehicleUnitFilter
    search_fields = [
        "stock_reference",
        "vin",
        "chassis_number",
        "variant__name",
        "variant__model__name",
        "variant__model__brand__name",
    ]
    ordering_fields = ["created_at", "current_price", "manufacture_year", "stock_reference"]
    ordering = ["-created_at", "-id"]
    permission_code_map = {
        "reserve": "reservation.create",
        "release_reservation": "reservation.release",
        "receive": "stock.receive",
        "transfer": "stock.transfer",
        "block": "vehicle.change_status",
        "unblock": "vehicle.change_status",
        "price_history": "vehicle.view_price_history",
        "change_price": "vehicle.change_price",
        "images": "vehicle.manage_images",
        "qr_code": "vehicle.generate_qr",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VehicleUnit.objects.none()
        return VehicleUnit.objects.select_related(
            "variant__model__brand",
            "variant__model__category",
            "current_location",
        ).prefetch_related("images")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = run_service(
            create_vehicle_unit,
            actor=request.user,
            validated_data=serializer.validated_data,
            request=request,
        )
        output = self.get_serializer(vehicle)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        vehicle = self.get_object()
        serializer = self.get_serializer(vehicle, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            update_vehicle_unit,
            vehicle=vehicle,
            actor=request.user,
            validated_data=serializer.validated_data,
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(
        request=CreateVehicleReservationSerializer,
        responses={201: VehicleReservationSerializer},
        summary="Reserve a vehicle for a customer",
    )
    @action(detail=True, methods=["post"], url_path="reserve")
    def reserve(self, request, pk=None):
        vehicle = self.get_object()
        serializer = CreateVehicleReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = run_service(
            reserve_vehicle,
            vehicle=vehicle,
            customer=serializer.validated_data["customer"],
            actor=request.user,
            expires_at=serializer.validated_data.get("expires_at"),
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response(
            {"id": reservation.pk, "reference": reservation.reference, "status": reservation.status},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ReleaseReservationSerializer, responses=OpenApiResponse(description="Reservation released."))
    @action(detail=True, methods=["post"], url_path="release-reservation")
    def release_reservation(self, request, pk=None):
        vehicle = self.get_object()
        reservation = VehicleReservation.objects.filter(
            vehicle=vehicle,
            status=VehicleReservation.ACTIVE,
        ).first()
        if reservation is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No active reservation exists for this vehicle.")
        serializer = ReleaseReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        released = run_service(
            release_reservation,
            reservation=reservation,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response({"reference": released.reference, "status": released.status})

    @extend_schema(request=ReceiveVehicleSerializer)
    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ReceiveVehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            receive_vehicle,
            vehicle=vehicle,
            location=serializer.validated_data["location"],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(request=TransferVehicleSerializer)
    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        vehicle = self.get_object()
        serializer = TransferVehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            transfer_vehicle,
            vehicle=vehicle,
            to_location=serializer.validated_data["to_location"],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(request=VehicleStatusReasonSerializer)
    @action(detail=True, methods=["post"], url_path="block")
    def block(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleStatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            block_vehicle,
            vehicle=vehicle,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(request=VehicleStatusReasonSerializer)
    @action(detail=True, methods=["post"], url_path="unblock")
    def unblock(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleStatusReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            unblock_vehicle,
            vehicle=vehicle,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(request=ChangeVehiclePriceSerializer, responses=VehicleUnitSerializer)
    @action(detail=True, methods=["post"], url_path="change-price")
    def change_price(self, request, pk=None):
        vehicle = self.get_object()
        serializer = ChangeVehiclePriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = run_service(
            change_vehicle_price,
            vehicle=vehicle,
            new_price=serializer.validated_data["new_price"],
            currency=serializer.validated_data.get("currency"),
            reason=serializer.validated_data.get("reason", ""),
            actor=request.user,
            request=request,
        )
        return Response(self.get_serializer(updated).data)

    @extend_schema(responses=VehiclePriceHistorySerializer(many=True))
    @action(detail=True, methods=["get"], url_path="price-history")
    def price_history(self, request, pk=None):
        vehicle = self.get_object()
        history = vehicle.price_history.all().select_related("changed_by")
        page = self.paginate_queryset(history)
        serializer = VehiclePriceHistorySerializer(page or history, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(request=VehicleImageSerializer, responses=VehicleImageSerializer)
    @action(detail=True, methods=["post"], url_path="images", parser_classes=[MultiPartParser, FormParser])
    def images(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = run_service(
            add_vehicle_image,
            vehicle=vehicle,
            actor=request.user,
            file_obj=serializer.validated_data.get("file"),
            is_primary=serializer.validated_data.get("is_primary", False),
            sort_order=serializer.validated_data.get("sort_order", 0),
            caption=serializer.validated_data.get("caption", ""),
            request=request,
        )
        return Response(VehicleImageSerializer(image).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Vehicle QR code as PNG.",
            )
        }
    )
    @action(detail=True, methods=["get"], url_path="qr-code")
    def qr_code(self, request, pk=None):
        vehicle = self.get_object()
        payload = run_service(generate_vehicle_qr, vehicle=vehicle, actor=request.user)
        response = HttpResponse(payload, content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="{vehicle.stock_reference}.png"'
        return response
