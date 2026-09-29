"""Authentication orchestration and token issuance."""

from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from core.events import user_login_failed, user_login_succeeded
from users.models import AccountStatus, UserSecurityProfile

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


class AuthenticationService:
    def login(
        self,
        *,
        identifier,
        password,
        request=None,
        device_name="",
        platform="",
    ):
        user = self._resolve_user(identifier)
        if user is None:
            user_login_failed.send(
                sender=None,
                user=None,
                identifier=identifier,
                request=request,
            )
            raise AuthenticationFailed("Invalid credentials.")

        from .twofa_service import TwoFAService

        profile = TwoFAService()._profile(user)
        with transaction.atomic():
            profile = (
                UserSecurityProfile.objects
                .select_for_update()
                .get(pk=profile.pk)
            )
            if profile.is_locked:
                failure_reason = "Account temporarily locked."
                authenticated = None
            elif not user.is_active:
                failure_reason = "Invalid credentials."
                authenticated = None
            else:
                authenticated = authenticate(
                    request=request,
                    username=user.username,
                    password=password,
                )
                failure_reason = (
                    "Invalid credentials."
                    if authenticated is None
                    else None
                )

            if authenticated is None:
                if not profile.is_locked and user.is_active:
                    profile.failed_login_count += 1
                    if profile.failed_login_count >= MAX_FAILED_ATTEMPTS:
                        profile.locked_until = timezone.now() + timedelta(
                            minutes=LOCK_MINUTES
                        )
                profile.last_security_event_at = timezone.now()
                profile.save(
                    update_fields=[
                        "failed_login_count",
                        "locked_until",
                        "last_security_event_at",
                    ]
                )
            else:
                profile.failed_login_count = 0
                profile.locked_until = None
                profile.last_security_event_at = timezone.now()
                profile.save(
                    update_fields=[
                        "failed_login_count",
                        "locked_until",
                        "last_security_event_at",
                    ]
                )

        if authenticated is None:
            user_login_failed.send(
                sender=user.__class__,
                user=user,
                identifier=identifier,
                request=request,
                reason=failure_reason,
            )
            if failure_reason == "Account temporarily locked.":
                raise AuthenticationFailed("Account temporarily locked.")
            raise AuthenticationFailed("Invalid credentials.")

        if user.account_status == AccountStatus.INVITED:
            raise AuthenticationFailed("Account onboarding is not complete.")

        if profile.two_factor_enabled:
            challenge, expires_at = TwoFAService().create_login_challenge(user)
            user_login_succeeded.send(
                sender=user.__class__,
                user=user,
                request=request,
                requires_2fa=True,
            )
            return {
                "requires_2fa": True,
                "challenge_token": challenge,
                "challenge_expires_at": expires_at,
            }

        setup = TwoFAService().setup(user)
        user_login_succeeded.send(
            sender=user.__class__,
            user=user,
            request=request,
            requires_2fa_setup=True,
        )
        return {
            "requires_2fa_setup": True,
            **setup,
        }

    def verify_2fa(
        self,
        *,
        challenge_token,
        code,
        request=None,
        device_name="",
        platform="",
    ):
        from .twofa_service import TwoFAService

        user = TwoFAService().verify_login_challenge(
            challenge_token,
            code,
            request=request,
        )
        return self.issue_tokens(
            user,
            request=request,
            device_name=device_name,
            platform=platform,
        )

    def issue_tokens(
        self,
        user,
        *,
        request=None,
        device_name="",
        platform="",
    ):
        profile = UserSecurityProfile.objects.filter(user=user).first()
        if (
            not user.is_active
            or user.account_status != AccountStatus.ACTIVE
            or not profile
            or not profile.two_factor_enabled
            or not profile.totp_secret_encrypted
            or not user.has_usable_password()
        ):
            raise AuthenticationFailed("Account onboarding is not complete.")
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
            "requires_2fa": False,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "session_id": str(session.id),
        }

    @staticmethod
    def _resolve_user(identifier):
        User = get_user_model()
        identifier = (identifier or "").strip()
        if not identifier:
            return None
        return (
            User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username=identifier).first()
        )
