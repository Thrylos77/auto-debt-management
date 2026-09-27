"""Regression tests for the canonical Users URL package."""

import pytest
from django.urls import reverse

import config.v1_urls as v1_urls
import users.urls as users_urls


@pytest.mark.django_db
def test_users_urls_package_aggregates_three_url_modules():
    package_dir = users_urls.__path__[0]

    names = {pattern.name for pattern in users_urls.urlpatterns if pattern.name}

    assert package_dir
    assert "auth-login" in names
    assert "user-list" in names
    assert "2fa-setup" in names


def test_users_urls_keep_expected_v1_paths():
    assert reverse("auth-login") == "/api/v1/auth/login/"
    assert reverse("user-list") == "/api/v1/users/"
    assert reverse("2fa-setup") == "/api/v1/users/me/2fa/setup/"


def test_config_v1_urls_only_points_to_users_urls_package():
    """Verify the actual Django URL resolvers instead of reading source files."""
    included_urlconfs = {
        getattr(urlconf, "__name__", urlconf)
        for pattern in v1_urls.urlpatterns
        if (urlconf := getattr(pattern, "urlconf_name", None)) is not None
    }

    assert "users.urls" in included_urlconfs
    assert "users.auth_urls" not in included_urlconfs


def test_legacy_compatibility_names_resolve_only_to_legacy_routes():
    assert reverse("token_obtain_pair") == "/api/users/token/login/"
    assert reverse("change-own-password") == "/api/users/change-own-password/"
    assert reverse(
        "change-password",
        kwargs={"pk": 1},
    ) == "/api/users/change-password/1/"
    assert reverse("request-otp") == "/api/users/request-otp/"
    assert reverse("reset-password") == "/api/users/reset-password/"


def test_legacy_user_names_do_not_shadow_canonical_v1_names():
    assert reverse("legacy-user-list") == "/api/users/"
    assert reverse("user-list") == "/api/v1/users/"
