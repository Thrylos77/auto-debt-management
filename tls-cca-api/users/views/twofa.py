"""Authenticated TOTP enrollment views."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from core.throttling import TwoFARateThrottle
from rbac.policies.permission_policy import AutoPermissionMixin
from users.serializers import (
    Enable2FASerializer, 
    VerifySetup2FASerializer,
    EmptyPasswordResetSerializer,
)
from users.services import TwoFAService

User = get_user_model()


@extend_schema(tags=["2FA"])
class Enable2FAView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = Enable2FASerializer

    def post(self, request):
        result = TwoFAService().setup(request.user)
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["2FA"])
class VerifySetup2FAView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifySetup2FASerializer
    throttle_classes = [TwoFARateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = TwoFAService().verify_setup(
            request.user,
            serializer.validated_data["setup_token"],
            serializer.validated_data["code"],
            request=request,
        )
        return Response(
            {"detail": "2FA has been enabled successfully.", "two_factor_enabled": True},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Security"])
class AdminReset2FAView(AutoPermissionMixin, generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = EmptyPasswordResetSerializer
    resource = "user.security"
    permission_code_map = {
        "POST": "reset_2fa",
        "PUT": "reset_2fa",
    }

    def post(self, request, *args, **kwargs):
        target = self.get_object()
        TwoFAService().reset_by_admin(
            target,
            actor=request.user,
            request=request,
        )
        return Response(
            {"detail": "Authenticator reset. A new enrollment link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )

    put = post
