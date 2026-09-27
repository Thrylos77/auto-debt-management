import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import UserPreference, UserSecurityProfile

User = get_user_model()


def make_user(**extra):
    values = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "ValidPassword1!",
        "first_name": "Alice",
        "last_name": "Example",
    }
    values.update(extra)
    return User.objects.create_user(**values)


@pytest.mark.django_db
def test_user_creation_bootstraps_identity_profiles():
    user = make_user()
    assert UserPreference.objects.filter(user=user).exists()
    assert UserSecurityProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_register_serializer_does_not_expose_rbac_fields():
    from users.serializers import RegisterSerializer
    assert "roles" not in RegisterSerializer().fields
    assert "groups" not in RegisterSerializer().fields


@pytest.mark.django_db
def test_v1_login_without_2fa_returns_tokens():
    user = make_user()
    client = APIClient()
    response = client.post(
        reverse("auth-login"),
        {"identifier": user.email, "password": "ValidPassword1!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["requires_2fa"] is False
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["session_id"]


@pytest.mark.django_db
def test_2fa_login_does_not_issue_access_token_at_first_step():
    user = make_user()
    profile = UserSecurityProfile.objects.get(user=user)
    profile.two_factor_enabled = True
    # Use a deterministic test secret to keep the contract test independent from QR generation.
    from users.services.twofa_service import encrypt_secret
    secret = "JBSWY3DPEHPK3PXP"
    profile.totp_secret_encrypted = encrypt_secret(secret)
    profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted"])
    user.is_2fa_enabled = True
    user.totp_secret = None
    user.save(update_fields=["is_2fa_enabled", "totp_secret"])

    response = APIClient().post(
        reverse("auth-login"),
        {"identifier": user.email, "password": "ValidPassword1!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["requires_2fa"] is True
    assert response.data["challenge_token"]
    assert "access" not in response.data
    assert "refresh" not in response.data



def _field_names_from_fieldsets(fieldsets):
    return [field for _, options in fieldsets for field in options["fields"]]


def test_custom_user_admin_has_no_duplicate_fields():
    from users.admin import CustomUserAdmin

    field_names = _field_names_from_fieldsets(CustomUserAdmin.fieldsets)
    assert len(field_names) == len(set(field_names))


def test_twofa_index_names_fit_django_database_limit():
    from users.models import TwoFAChallenge, TwoFASetup

    for model in (TwoFAChallenge, TwoFASetup):
        index_names = [index.name for index in model._meta.indexes]
        assert index_names
        assert all(len(name) <= 30 for name in index_names)


@pytest.mark.django_db(transaction=True)
def test_revoke_all_sessions_emits_audit_events():
    from datetime import timedelta
    from django.utils import timezone
    from rest_framework_simplejwt.tokens import RefreshToken
    from audit.models import AuditEvent
    from users.models import UserSession
    from users.services.session_service import SessionService

    user = User.objects.create_user(username="session-audit", email="session-audit@example.com", password="x")
    token = RefreshToken.for_user(user)
    UserSession.objects.create(
        user=user, expires_at=timezone.now() + timedelta(hours=1), jti=str(token["jti"])
    )
    assert SessionService().revoke_all_sessions(user, actor=user) == 1
    assert AuditEvent.objects.filter(action="session.revoke_all", actor_user=user).exists()


@pytest.mark.django_db
def test_invalid_twofa_code_emits_failure_audit_event():
    from audit.models import AuditEvent
    from users.models import UserSecurityProfile, TwoFAChallenge
    from users.services.twofa_service import TwoFAService, encrypt_secret
    from rest_framework.exceptions import ValidationError

    user = make_user(username="twofa-audit-failure", email="twofa-audit-failure@example.com")
    profile = UserSecurityProfile.objects.get(user=user)
    profile.two_factor_enabled = True
    profile.totp_secret_encrypted = encrypt_secret("JBSWY3DPEHPK3PXP")
    profile.save(update_fields=["two_factor_enabled", "totp_secret_encrypted"])
    challenge, _ = TwoFAService().create_login_challenge(user)
    with pytest.raises(ValidationError):
        TwoFAService().verify_login_challenge(challenge, "000000")
    challenge_id = challenge.split(".", 1)[0]
    assert TwoFAChallenge.objects.get(pk=challenge_id).attempts == 1
    assert AuditEvent.objects.filter(action="login.2fa_failure", status="failure", actor_user=user).exists()


@pytest.mark.django_db
def test_failed_login_persists_security_counter_and_audit():
    from audit.models import AuditEvent
    from users.models import UserSecurityProfile
    from users.services.authentication import AuthenticationService
    from rest_framework.exceptions import AuthenticationFailed

    user = make_user(username="login-audit-failure", email="login-audit-failure@example.com")
    with pytest.raises(AuthenticationFailed):
        AuthenticationService().login(
            identifier=user.email,
            password="wrong-password",
        )
    profile = UserSecurityProfile.objects.get(user=user)
    assert profile.failed_login_count == 1
    assert AuditEvent.objects.filter(action="login.failure", status="failure", actor_user=user).exists()


@pytest.mark.django_db
def test_logout_cannot_revoke_another_users_refresh_token():
    from rest_framework_simplejwt.tokens import RefreshToken
    from users.models import UserSession
    from users.services.session_service import SessionService
    from rest_framework.exceptions import ValidationError

    owner = make_user(username="refresh-owner", email="refresh-owner@example.com")
    other = make_user(username="refresh-other", email="refresh-other@example.com")
    token = RefreshToken.for_user(owner)
    session = UserSession.objects.create(
        user=owner, expires_at=timezone.now() + timedelta(hours=1), jti=str(token["jti"])
    )
    with pytest.raises(ValidationError):
        SessionService().revoke_refresh_token(str(token), actor=other)
    session.refresh_from_db()
    assert session.revoked_at is None
