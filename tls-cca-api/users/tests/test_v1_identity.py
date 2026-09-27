import pytest
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
