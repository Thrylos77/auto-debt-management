from drf_spectacular.utils import extend_schema
from django.utils import timezone as django_timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from core.throttling import LoginRateThrottle, TwoFARateThrottle
from users.serializers.auth import Login2FASerializer, LoginSerializer, LogoutSerializer
from users.services.authentication import AuthenticationService
from users.services.session_service import SessionService
from core.events import user_logout


@extend_schema(tags=["Authentication"])
class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthenticationService().login(
            identifier=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
            request=request,
            device_name=serializer.validated_data.get("device_name", ""),
            platform=serializer.validated_data.get("platform", ""),
        )
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class VerifyTwoFALoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = Login2FASerializer
    throttle_classes = [TwoFARateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthenticationService().verify_2fa(
            challenge_token=serializer.validated_data["challenge_token"],
            code=serializer.validated_data["code"],
            request=request,
            device_name=serializer.validated_data.get("device_name", ""),
            platform=serializer.validated_data.get("platform", ""),
        )
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        SessionService().revoke_refresh_token(serializer.validated_data["refresh"], actor=request.user, request=request)
        user_logout.send(sender=request.user.__class__, user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        old_refresh = request.data.get("refresh")
        old_jti = None
        user = None
        token_family = None
        if old_refresh:
            try:
                old_token = RefreshToken(old_refresh)
                old_jti = str(old_token["jti"])
                user_id = old_token.get("user_id")
                if user_id:
                    from django.contrib.auth import get_user_model
                    user = get_user_model().objects.filter(pk=user_id).first()
                from users.models import UserSession
                old_session = UserSession.objects.filter(jti=old_jti).first()
                if old_session:
                    token_family = old_session.token_family
            except TokenError:
                pass

        response = super().post(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK or not response.data.get("refresh") or user is None:
            return response

        if old_jti:
            from users.services.session_service import SessionService
            from users.models import UserSession
            SessionService()._blacklist_jti(old_jti)
            UserSession.objects.filter(jti=old_jti, revoked_at__isnull=True).update(revoked_at=django_timezone.now())
            new_refresh = RefreshToken(response.data["refresh"])
            session = SessionService().create_session(user=user, refresh_token=new_refresh, request=request)
            if token_family is not None:
                session.token_family = token_family
                session.save(update_fields=["token_family"])
            response.data["session_id"] = str(session.id)
        return response


class VerifyTokenView(TokenVerifyView):
    permission_classes = [permissions.AllowAny]
