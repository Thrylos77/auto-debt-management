"""
users/views/views_2fa.py

2FA / TOTP views for enabling, verifying, and logging in with 2FA.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model

from users.serializers import (
    Enable2FASerializer, VerifySetup2FASerializer,
    Disable2FASerializer, Login2FASerializer,
)
from users.services import twofa_services

User = get_user_model()

# Durée de vie du token temporaire pour l'étape 2FA (5 minutes)
TEMP_TOKEN_LIFETIME_MINUTES = 5


@extend_schema(tags=["2FA"])
class Enable2FAView(generics.GenericAPIView):
    """
    Étape 1 : Génère un secret TOTP et retourne le QR code.
    L'utilisateur scanne ce QR code avec Google Authenticator.
    """
    serializer_class = Enable2FASerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_2fa_enabled:
            return Response(
                {"detail": "2FA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = twofa_services.generate_totp_secret()
        uri = twofa_services.get_totp_uri(user, secret)
        qr_code = twofa_services.generate_qr_code_base64(uri)

        return Response({
            "secret": secret,
            "uri": uri,
            "qrcode": qr_code,
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["2FA"])
class VerifySetup2FAView(generics.GenericAPIView):
    """
    Étape 2 : Vérifie le premier code TOTP pour confirmer l'activation.
    L'utilisateur doit fournir le secret de l'étape 1 et un code valide.
    """
    serializer_class = VerifySetup2FASerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.is_2fa_enabled:
            return Response(
                {"detail": "2FA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']

        # Le secret doit avoir été fourni à l'étape précédente.
        # Le client doit le renvoyer (ou on pourrait le stocker temporairement).
        secret = request.data.get('secret')
        if not secret:
            return Response(
                {"detail": "Secret is required. Call /api/2fa/enable/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        twofa_services.enable_2fa(user, secret, code)
        return Response({
            "detail": "2FA has been enabled successfully.",
            "is_2fa_enabled": True,
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["2FA"])
class Disable2FAView(generics.GenericAPIView):
    """
    Désactive le 2FA pour l'utilisateur connecté.
    Nécessite le mot de passe pour des raisons de sécurité.
    """
    serializer_class = Disable2FASerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_2fa_enabled:
            return Response(
                {"detail": "2FA is not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']

        twofa_services.disable_2fa(user, password)
        return Response({
            "detail": "2FA has been disabled.",
            "is_2fa_enabled": False,
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["2FA"])
class Login2FAView(generics.GenericAPIView):
    """
    Seconde étape de connexion lorsque le 2FA est activé.
    Fournissez le temp_token (obtenu via /api/token/login/) et un code TOTP.
    Retourne les vrais tokens d'accès et de rafraîchissement.
    """
    serializer_class = Login2FASerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        temp_token_str = serializer.validated_data['temp_token']
        code = serializer.validated_data['code']

        # Validation du token temporaire
        try:
            temp_token = AccessToken(temp_token_str)
            user_id = temp_token.payload.get('user_id')
            is_2fa_temp = temp_token.payload.get('is_2fa_temp', False)
        except TokenError:
            return Response(
                {"detail": "Invalid or expired temp token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not is_2fa_temp:
            return Response(
                {"detail": "Invalid token type."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Récupération de l'utilisateur
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Vérification du code TOTP
        if not twofa_services.verify_totp_code(user.totp_secret, code):
            return Response(
                {"code": "Invalid TOTP code."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Génération des vrais tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)