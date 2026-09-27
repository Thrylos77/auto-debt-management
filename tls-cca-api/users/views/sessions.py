from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.models import UserSession
from users.policies.session_policy import SessionPolicy
from users.serializers.sessions import UserSessionSerializer
from users.serializers.users import (
    EmptyRequestSerializer,
    SessionActionResponseSerializer,
)
from users.services.session_service import SessionService


@extend_schema(tags=["Sessions"])
class SessionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return UserSession.objects.none()

        return SessionService().list_user_sessions(self.request.user)


@extend_schema(tags=["Sessions"])
class SessionRevokeView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSessionSerializer
    lookup_url_kwarg = "session_id"

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        session = get_object_or_404(self.get_queryset(), pk=kwargs[self.lookup_url_kwarg])
        if not SessionPolicy.can_revoke(request.user, session):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to revoke this session.")
        SessionService().revoke_session(session, actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Sessions"])
class SessionRevokeAllView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmptyRequestSerializer

    @extend_schema(
        summary="Revoke all user sessions",
        request=None,
        responses=SessionActionResponseSerializer,
    )
    def post(self, request):
        SessionService().revoke_all_sessions(request.user, actor=request.user, request=request)
        return Response({"detail": "All sessions revoked."}, status=status.HTTP_200_OK)
