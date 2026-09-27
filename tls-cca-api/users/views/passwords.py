from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from core.throttling import OTPRateThrottle, PasswordResetRateThrottle
from rbac.policies.permission_policy import AutoPermissionMixin
from users.serializers.passwords import AdminChangePasswordSerializer, ChangeOwnPasswordSerializer, RequestOTPSerializer, ResetPasswordSerializer
from users.services.password_service import PasswordService
from users.services import otp_service

User = get_user_model()


@extend_schema(tags=["Users", "Passwords"])
class ChangeOwnPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeOwnPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        PasswordService().change_password(
            request.user,
            serializer.validated_data["new_password"],
            old_password=serializer.validated_data["old_password"],
            actor=request.user,
            request=request,
        )
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

    put = post


@extend_schema(tags=["Users", "Passwords"])
class AdminChangePasswordView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = AdminChangePasswordSerializer
    queryset = User.objects.all()
    resource = "user"
    permission_code_map = {"PUT": "change_password", "POST": "change_password"}

    def post(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        target = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        serializer = self.get_serializer(data=request.data, context={"request": request, "target_user": target})
        serializer.is_valid(raise_exception=True)
        PasswordService().change_password(
            target,
            serializer.validated_data["new_password"],
            actor=request.user,
            force=True,
            request=request,
        )
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


class RequestOTPView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RequestOTPSerializer
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user:
            try:
                otp_service.request_password_reset_otp(user)
            except ValidationError:
                # Do not disclose whether the account exists or whether a cooldown
                # is active. The rate throttle remains the public anti-abuse control.
                pass
        return Response({"detail": "If the account exists, an OTP will be sent."}, status=status.HTTP_200_OK)

    create = post


class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if not user:
            return Response({"detail": "Unable to reset password."}, status=status.HTTP_400_BAD_REQUEST)
        otp_service.reset_password_with_otp(user, serializer.validated_data["otp"], serializer.validated_data["new_password"], request=request)
        return Response({"detail": "Password reset successfully."}, status=status.HTTP_200_OK)

    create = post
