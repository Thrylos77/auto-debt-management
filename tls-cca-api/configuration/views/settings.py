"""REST API for registered platform configuration."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from configuration.models import SystemSetting
from configuration.policies import ConfigurationPolicy
from configuration.serializers import (
    SystemSettingSerializer,
    SystemSettingWriteSerializer,
)
from configuration.services import ConfigurationService, ConfigurationTypeCodec


@extend_schema(tags=["Configuration"])
class ConfigurationSettingListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SystemSettingSerializer
    queryset = SystemSetting.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SystemSetting.objects.none()
        if not ConfigurationPolicy.can_list(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You do not have permission to list configuration settings."
            )
        return ConfigurationService.list_settings()


@extend_schema(tags=["Configuration"])
class ConfigurationSettingDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SystemSettingWriteSerializer

    def get_object(self):
        return ConfigurationService.get_record(self.kwargs["key"])

    @extend_schema(
        summary="Get one configuration setting",
        responses=OpenApiResponse(response=SystemSettingSerializer),
    )
    def get(self, request, *args, **kwargs):
        if not ConfigurationPolicy.can_view(request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You do not have permission to view configuration settings."
            )

        setting = self.get_object()
        if setting is None:
            definition = ConfigurationService.get_definition_or_raise(
                kwargs["key"]
            )
            # Unpersisted defaults are represented by a transient object only
            # for response serialization; GET remains side-effect free.
            setting = SystemSetting(
                key=definition.key,
                category=definition.category,
                value=ConfigurationTypeCodec.encode(
                    definition.default,
                    definition.value_type,
                ),
                description=definition.description,
                value_type=definition.value_type,
                is_public=definition.is_public,
                scope=definition.scope,
            )

        return Response(
            SystemSettingSerializer(
                setting,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update one configuration setting",
        request=SystemSettingWriteSerializer,
        responses=OpenApiResponse(response=SystemSettingSerializer),
    )
    def put(self, request, *args, **kwargs):
        if not ConfigurationPolicy.can_update(request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have permission to update configuration settings.")

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request,
                "key": kwargs["key"],
            },
        )
        serializer.is_valid(raise_exception=True)
        setting = ConfigurationService.set(
            kwargs["key"],
            serializer.validated_data["value"],
            actor=request.user,
            request=request,
            description=serializer.validated_data.get("description"),
            is_public=serializer.validated_data.get("is_public"),
        )
        return Response(
            SystemSettingSerializer(
                setting,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )
