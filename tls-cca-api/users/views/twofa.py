from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from core.throttling import TwoFARateThrottle
from users.policies.twofa_policy import TwoFAPolicy
from users.serializers.twofa import Disable2FASerializer, Enable2FASerializer, VerifySetup2FASerializer
from users.services.twofa_service import TwoFAService


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
        recovery_codes = TwoFAService().verify_setup(
            request.user,
            serializer.validated_data["setup_token"],
            serializer.validated_data["code"],
            request=request,
        )
        return Response({"detail": "2FA has been enabled successfully.", "two_factor_enabled": True, "recovery_codes": recovery_codes}, status=status.HTTP_200_OK)


@extend_schema(tags=["2FA"])
class Disable2FAView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = Disable2FASerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not TwoFAPolicy.can_manage(request.user, request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to manage 2FA.")
        TwoFAService().disable(request.user, serializer.validated_data["password"], request=request)
        return Response({"detail": "2FA has been disabled.", "two_factor_enabled": False}, status=status.HTTP_200_OK)
