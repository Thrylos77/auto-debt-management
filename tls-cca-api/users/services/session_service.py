from datetime import datetime, timezone
from django.db import transaction
from django.utils import timezone as django_timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from audit.services import AuditService
from users.models import UserSession
from users.events import user_session_revoked


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
    def revoke_session(self, session: UserSession, *, actor=None, request=None):
        if session.revoked_at is not None:
            return session
        self._blacklist_jti(session.jti)
        session.revoked_at = django_timezone.now()
        session.save(update_fields=["revoked_at"])
        transaction.on_commit(lambda: user_session_revoked.send(
            sender=session.__class__, user=session.user, actor=actor, session=session,
            request=request,
        ))
        return session

    @transaction.atomic
    def revoke_all_sessions(self, user, *, actor=None, request=None):
        sessions = list(UserSession.objects.select_for_update().filter(user=user, revoked_at__isnull=True))
        now = django_timezone.now()
        for session in sessions:
            self._blacklist_jti(session.jti)
            session.revoked_at = now
            session.save(update_fields=["revoked_at"])
            transaction.on_commit(lambda session=session: user_session_revoked.send(
                sender=session.__class__, user=session.user, actor=actor, session=session,
                request=request, reason="all_sessions",
            ))
        return len(sessions)

    def mark_seen(self, session: UserSession):
        session.last_seen_at = django_timezone.now()
        session.save(update_fields=["last_seen_at"])
        return session

    def revoke_refresh_token(self, token_string: str, *, actor=None, request=None):
        try:
            refresh = RefreshToken(token_string)
            jti = str(refresh["jti"])
            refresh_user_id = refresh.get("user_id")
        except (TokenError, KeyError, TypeError, ValueError) as exc:
            raise ValidationError({"refresh": "Token is invalid or expired."}) from exc

        if actor is not None and str(refresh_user_id) != str(actor.pk):
            AuditService.record(
                actor=actor, category="AUTHORIZATION", action="session.refresh_revoke",
                status="denied", reason="Refresh token does not belong to current user.",
                request=request,
            )
            raise ValidationError({"refresh": "Token does not belong to the current user."})

        with transaction.atomic():
            session = UserSession.objects.filter(jti=jti, revoked_at__isnull=True).first()
            if actor is not None and session is not None and session.user_id != actor.pk:
                AuditService.record(
                    actor=actor, category="AUTHORIZATION", action="session.refresh_revoke",
                    resource=session, status="denied", reason="Session does not belong to current user.",
                    request=request,
                )
                raise ValidationError({"refresh": "Token does not belong to the current user."})
            self._blacklist_jti(jti)
            if session:
                session.revoked_at = django_timezone.now()
                session.save(update_fields=["revoked_at"])
                transaction.on_commit(lambda: user_session_revoked.send(
                    sender=session.__class__, user=session.user, actor=actor, session=session,
                    request=request, reason="refresh_token",
                ))

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
