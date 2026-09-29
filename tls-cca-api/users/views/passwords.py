"""Password change and recovery views."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from core.throttling import PasswordResetRateThrottle
from rbac.policies.permission_policy import AutoPermissionMixin
from users.models import AccountStatus, PasswordResetChallenge
from users.serializers import (
    ChangeOwnPasswordSerializer,
    EmptyPasswordResetSerializer,
    RequestPasswordResetSerializer,
    ResetPasswordSerializer,
)
from users.services import (
    PasswordRecoveryService, 
    PasswordService
)

User = get_user_model()


@extend_schema(tags=["Users", "Passwords"])
class ChangeOwnPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeOwnPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        PasswordService().change_own_password(
            request.user,
            serializer.validated_data["old_password"],
            serializer.validated_data["new_password"],
            serializer.validated_data["totp_code"],
            request=request,
        )
        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

    put = post


@extend_schema(tags=["Users", "Passwords", "Security"])
class AdminRequestPasswordResetView(
    AutoPermissionMixin,
    generics.GenericAPIView,
):
    queryset = User.objects.all()
    serializer_class = EmptyPasswordResetSerializer
    resource = "user.security"
    permission_code_map = {
        "POST": "reset_password",
        "PUT": "reset_password",
    }

    def post(self, request, *args, **kwargs):
        target = self.get_object()
        PasswordRecoveryService().issue(
            target,
            requested_by=request.user,
            purpose=PasswordResetChallenge.ADMIN_TRIGGERED,
            request=request,
        )
        return Response(
            {"detail": "A password reset link has been sent to the user."},
            status=status.HTTP_202_ACCEPTED,
        )

    put = post


@extend_schema(tags=["Authentication", "Passwords"])
class RequestPasswordResetView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RequestPasswordResetSerializer
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"],
        ).first()
        if user and user.is_active and user.account_status == AccountStatus.ACTIVE:
            try:
                PasswordRecoveryService().issue(user, request=request)
            except ValidationError:
                # Public recovery must not disclose whether the submitted email
                # maps to an account eligible for self-service recovery.
                pass

        return Response(
            {"detail": "If the account is eligible, a reset link will be sent."},
            status=status.HTTP_200_OK,
        )

    create = post


@extend_schema(tags=["Authentication", "Passwords"])
class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordRecoveryService().complete(
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
            totp_code=serializer.validated_data.get("totp_code"),
            request=request,
        )
        return Response(
            {"detail": "Password reset successfully. Please sign in again."},
            status=status.HTTP_200_OK,
        )

    create = post
