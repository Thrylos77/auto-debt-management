"""Regression tests for removal of legacy User compatibility fields."""

from django.contrib.auth import get_user_model


def test_user_has_no_legacy_rbac_or_totp_fields():
    User = get_user_model()
    field_names = {field.name for field in User._meta.get_fields()}

    assert "roles" not in field_names
    assert "totp_secret" not in field_names
    assert "is_2fa_enabled" not in field_names

    # ``AbstractUser`` intentionally keeps Django's own auth.Group relation.
    # The legacy application RBAC ``User.groups -> rbac.Group`` relation has
    # been removed and must never return.
    groups_field = User._meta.get_field("groups")
    assert groups_field.remote_field.model._meta.label == "auth.Group"


def test_user_has_no_legacy_permission_accessors():
    User = get_user_model()

    assert not hasattr(User, "all_permissions")
    assert not hasattr(User, "has_permission")
