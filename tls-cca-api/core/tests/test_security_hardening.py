"""Regression tests for final API security hardening."""

import json

import pytest
from django.conf import settings
from django.test import override_settings
from django.test.client import RequestFactory
from django.http import HttpResponse

from core.middleware.request_limits import RequestBodySizeLimitMiddleware


def test_request_size_middleware_rejects_oversized_api_bodies():
    factory = RequestFactory()
    request = factory.post(
        "/api/v1/users/",
        data=b"x",
        content_type="application/octet-stream",
    )
    request.META["CONTENT_LENGTH"] = "11"

    middleware = RequestBodySizeLimitMiddleware(lambda request: HttpResponse("ok"))

    with override_settings(API_MAX_REQUEST_BYTES=10):
        response = middleware(request)

    assert response.status_code == 413
    assert json.loads(response.content.decode("utf-8")) == {
        "detail": "Request body too large."
    }


def test_request_size_middleware_allows_bodies_under_the_limit():
    factory = RequestFactory()
    request = factory.post(
        "/api/v1/users/",
        data=b"x",
        content_type="application/octet-stream",
    )
    request.META["CONTENT_LENGTH"] = "10"

    middleware = RequestBodySizeLimitMiddleware(lambda request: HttpResponse("ok"))

    with override_settings(API_MAX_REQUEST_BYTES=10):
        response = middleware(request)

    assert response.status_code == 200


def test_request_size_middleware_does_not_limit_non_api_paths():
    factory = RequestFactory()
    request = factory.post(
        "/admin/",
        data=b"x",
        content_type="application/octet-stream",
    )
    request.META["CONTENT_LENGTH"] = "999999"

    middleware = RequestBodySizeLimitMiddleware(lambda request: HttpResponse("ok"))

    with override_settings(API_MAX_REQUEST_BYTES=10):
        response = middleware(request)

    assert response.status_code == 200


def test_request_size_middleware_ignores_malformed_content_length():
    factory = RequestFactory()
    request = factory.post(
        "/api/v1/users/",
        data=b"x",
        content_type="application/octet-stream",
    )
    request.META["CONTENT_LENGTH"] = "not-a-number"

    middleware = RequestBodySizeLimitMiddleware(lambda request: HttpResponse("ok"))

    with override_settings(API_MAX_REQUEST_BYTES=10):
        response = middleware(request)

    assert response.status_code == 200


def test_security_settings_are_explicit():
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.SECURE_CROSS_ORIGIN_OPENER_POLICY == "same-origin"
    assert settings.X_FRAME_OPTIONS == "DENY"
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"


def test_cors_is_not_open_by_default():
    assert settings.CORS_ALLOW_ALL_ORIGINS is False
    assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
    assert settings.CORS_ALLOW_CREDENTIALS is False
    assert settings.CORS_URLS_REGEX == r"^/api(?:/|$)"


def test_jwt_hardening_settings_are_enabled():
    assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True
    assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True
    assert settings.SIMPLE_JWT["CHECK_REVOKE_TOKEN"] is True
    assert settings.SIMPLE_JWT["REVOKE_TOKEN_CLAIM"] == "prv"
    assert settings.SIMPLE_JWT["CHECK_USER_IS_ACTIVE"] is True
    assert settings.SIMPLE_JWT["LEEWAY"] == 0
    assert settings.SIMPLE_JWT["AUTH_HEADER_TYPES"] == ("Bearer",)


@pytest.mark.django_db
def test_sensitive_auth_views_keep_explicit_throttles():
    from users.views import (
        LoginView,
        RequestOTPView,
        ResetPasswordView,
        VerifySetup2FAView,
        VerifyTwoFALoginView,
    )

    from core.throttling import LoginRateThrottle, OTPRateThrottle, PasswordResetRateThrottle, TwoFARateThrottle

    assert LoginRateThrottle in LoginView.throttle_classes
    assert TwoFARateThrottle in VerifyTwoFALoginView.throttle_classes
    assert TwoFARateThrottle in VerifySetup2FAView.throttle_classes
    assert OTPRateThrottle in RequestOTPView.throttle_classes
    assert PasswordResetRateThrottle in ResetPasswordView.throttle_classes
