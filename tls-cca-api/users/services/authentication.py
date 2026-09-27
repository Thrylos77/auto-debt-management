from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from users.events import user_login_failed, user_login_succeeded
from users.models import UserSecurityProfile

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


class AuthenticationService:
    @transaction.atomic
    def login(self, *, identifier, password, request=None, device_name="", platform=""):
        user = self._resolve_user(identifier)
        if user is None:
            self._record_failure(None, identifier, request)
            raise AuthenticationFailed("Invalid credentials.")

        from .twofa_service import TwoFAService
        profile = TwoFAService()._profile(user)
        profile = UserSecurityProfile.objects.select_for_update().get(pk=profile.pk)
        if profile.is_locked:
            raise AuthenticationFailed("Account temporarily locked.")
        if not user.is_active:
            self._record_failure(user, identifier, request)
            raise AuthenticationFailed("Invalid credentials.")

        authenticated = authenticate(request=request, username=user.username, password=password)
        if authenticated is None:
            self._record_failure(user, identifier, request)
            raise AuthenticationFailed("Invalid credentials.")

        profile.failed_login_count = 0
        profile.locked_until = None
        profile.last_security_event_at = timezone.now()
        profile.save(update_fields=["failed_login_count", "locked_until", "last_security_event_at"])

        twofa_enabled = bool(profile.two_factor_enabled or user.is_2fa_enabled)
        if twofa_enabled:
            challenge, expires_at = TwoFAService().create_login_challenge(user)
            user_login_succeeded.send(sender=user.__class__, user=user, request=request, requires_2fa=True)
            return {
                "requires_2fa": True,
                "challenge_token": challenge,
                "challenge_expires_at": expires_at,
            }

        tokens = self._issue_tokens(user, request=request, device_name=device_name, platform=platform)
        user_login_succeeded.send(sender=user.__class__, user=user, request=request, requires_2fa=False)
        return {"requires_2fa": False, **tokens}

    @transaction.atomic
    def verify_2fa(self, *, challenge_token, code, request=None, device_name="", platform=""):
        from .twofa_service import TwoFAService

        user = TwoFAService().verify_login_challenge(challenge_token, code)
        tokens = self._issue_tokens(user, request=request, device_name=device_name, platform=platform)
        return {"requires_2fa": False, **tokens}

    def _issue_tokens(self, user, *, request=None, device_name="", platform=""):
        refresh = RefreshToken.for_user(user)
        from .session_service import SessionService
        session = SessionService().create_session(
            user=user,
            refresh_token=refresh,
            request=request,
            device_name=device_name,
            platform=platform,
        )
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "session_id": str(session.id),
        }

    @staticmethod
    def _resolve_user(identifier):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        identifier = (identifier or "").strip()
        if not identifier:
            return None
        return User.objects.filter(email__iexact=identifier).first() or User.objects.filter(username=identifier).first()

    @staticmethod
    def _record_failure(user, identifier, request):
        if user is None:
            user_login_failed.send(sender=None, user=None, identifier=identifier, request=request)
            return
        profile = UserSecurityProfile.objects.get_or_create(user=user)[0]
        profile.failed_login_count += 1
        if profile.failed_login_count >= MAX_FAILED_ATTEMPTS:
            profile.locked_until = timezone.now() + timedelta(minutes=LOCK_MINUTES)
        profile.last_security_event_at = timezone.now()
        profile.save(update_fields=["failed_login_count", "locked_until", "last_security_event_at"])
        user_login_failed.send(sender=user.__class__, user=user, identifier=identifier, request=request)
