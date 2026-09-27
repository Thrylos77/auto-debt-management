from datetime import datetime, timezone
from django.db import transaction
from django.utils import timezone as django_timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserSession


class SessionService:
    @transaction.atomic
    def create_session(self, *, user, refresh_token, request=None, device_name="", platform=""):
        payload = refresh_token.payload if hasattr(refresh_token, "payload") else dict(refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        return UserSession.objects.create(
            user=user,
            expires_at=expires_at,
            ip_address=self._ip(request),
            user_agent=(request.headers.get("User-Agent", "")[:2000] if request else ""),
            device_name=device_name or "",
            platform=platform or "",
            jti=str(payload["jti"]),
        )

    def list_user_sessions(self, user):
        return UserSession.objects.filter(user=user).order_by("-created_at")

    @transaction.atomic
    def revoke_session(self, session: UserSession, *, actor=None):
        if session.revoked_at is not None:
            return session
        self._blacklist_jti(session.jti)
        session.revoked_at = django_timezone.now()
        session.save(update_fields=["revoked_at"])
        return session

    @transaction.atomic
    def revoke_all_sessions(self, user, *, actor=None):
        sessions = UserSession.objects.select_for_update().filter(user=user, revoked_at__isnull=True)
        for session in sessions:
            self._blacklist_jti(session.jti)
        return sessions.update(revoked_at=django_timezone.now())

    def mark_seen(self, session: UserSession):
        session.last_seen_at = django_timezone.now()
        session.save(update_fields=["last_seen_at"])
        return session

    @transaction.atomic
    def revoke_refresh_token(self, token_string: str):
        try:
            refresh = RefreshToken(token_string)
            jti = str(refresh["jti"])
            self._blacklist_jti(jti)
            UserSession.objects.filter(jti=jti, revoked_at__isnull=True).update(revoked_at=django_timezone.now())
        except Exception as exc:
            raise ValidationError({"refresh": "Token is invalid or expired."}) from exc

    @staticmethod
    def _blacklist_jti(jti: str):
        outstanding = OutstandingToken.objects.filter(jti=jti).first()
        if outstanding:
            BlacklistedToken.objects.get_or_create(token=outstanding)

    @staticmethod
    def _ip(request):
        if request is None:
            return None
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
