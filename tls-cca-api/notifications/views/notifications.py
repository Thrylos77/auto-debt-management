"""REST endpoints for the authenticated user's notifications."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from notifications.services import NotificationService


class NotificationReadAllResponseSerializer(serializers.Serializer):
    updated = serializers.IntegerField()


@extend_schema(tags=["Notifications"])
class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


@extend_schema(tags=["Notifications"])
class NotificationDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


@extend_schema(tags=["Notifications"])
class MarkNotificationReadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()

    @extend_schema(
        summary="Mark one notification as read",
        request=None,
        responses=OpenApiResponse(response=NotificationSerializer),
    )
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification.objects.filter(user=request.user),
            pk=kwargs["pk"],
        )
        NotificationService.mark_as_read(notification)
        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Notifications"])
class MarkAllNotificationsReadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationReadAllResponseSerializer

    @extend_schema(
        summary="Mark all notifications as read",
        request=None,
        responses=OpenApiResponse(
            response=NotificationReadAllResponseSerializer,
        ),
    )
    def post(self, request, *args, **kwargs):
        updated = NotificationService.mark_all_as_read(request.user)
        return Response(
            {"updated": updated},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Notifications"])
class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    def get_object(self):
        preference, _ = NotificationPreference.objects.get_or_create(
            user=self.request.user,
        )
        return preference
