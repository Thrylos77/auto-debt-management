"""Public onboarding and security-recovery views."""

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from core.throttling import TwoFARateThrottle
from rbac.policies.permission_policy import AutoPermissionMixin
from users.models import User
from users.serializers import (
    AcceptInvitationSerializer,
    TwoFARecoverySetupSerializer,
    TwoFARecoveryVerifySerializer,
    VerifyInvitationTwoFASerializer,
)
from users.serializers import EmptyRequestSerializer
from users.services import ( 
    AuthenticationService, 
    InvitationService, 
    TwoFAService,
)


@extend_schema(tags=["Authentication"])
class AcceptInvitationView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AcceptInvitationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setup = InvitationService().accept(
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
            request=request,
        )
        return Response(setup, status=status.HTTP_200_OK)


class _VerifySetupAndIssueTokensView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyInvitationTwoFASerializer
    throttle_classes = [TwoFARateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = TwoFAService().verify_setup_token(
            serializer.validated_data["setup_token"],
            serializer.validated_data["code"],
            request=request,
        )
        tokens = AuthenticationService().issue_tokens(
            user,
            request=request,
            device_name=serializer.validated_data.get("device_name", ""),
            platform=serializer.validated_data.get("platform", ""),
        )
        return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class VerifyInvitationTwoFAView(_VerifySetupAndIssueTokensView):
    """Complete TOTP enrollment after invitation acceptance."""


@extend_schema(tags=["Authentication"])
class VerifyInitialTwoFAView(_VerifySetupAndIssueTokensView):
    """Complete mandatory TOTP enrollment for an existing active account."""


@extend_schema(tags=["Authentication"])
class TwoFARecoverySetupView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TwoFARecoverySetupSerializer
    throttle_classes = [TwoFARateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setup = TwoFAService().get_setup_by_token(
            serializer.validated_data["setup_token"]
        )
        return Response(setup, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class TwoFARecoveryVerifyView(_VerifySetupAndIssueTokensView):
    """Complete a TOTP re-enrollment after administrative recovery."""

    serializer_class = TwoFARecoveryVerifySerializer


@extend_schema(tags=["Users", "Security"])
class ResendInvitationView(AutoPermissionMixin, generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = EmptyRequestSerializer
    resource = "user"
    permission_code_map = {"POST": "invite"}

    def post(self, request, *args, **kwargs):
        target = self.get_object()
        InvitationService().issue(target, actor=request.user, request=request)
        return Response(
            {"detail": "Invitation sent successfully."},
            status=status.HTTP_202_ACCEPTED,
        )
