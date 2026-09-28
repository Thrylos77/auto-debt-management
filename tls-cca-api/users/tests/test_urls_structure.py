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



def test_legacy_url_names_are_removed():
    """The final API surface must not expose pre-v1 named routes."""
    from django.urls import NoReverseMatch

    legacy_names = {
        "token_obtain_pair",
        "change-own-password",
        "change-password",
        "request-otp",
        "reset-password",
        "legacy-user-list",
    }

    for name in legacy_names:
        with pytest.raises(NoReverseMatch):
            reverse(name, kwargs={"pk": 1} if name == "change-password" else None)
