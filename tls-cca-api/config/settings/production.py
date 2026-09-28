"""Production settings overlay with fail-fast security checks."""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

if SECRET_KEY == "dev-only-change-this-secret-key":
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")
if "DB_NAME" not in os.environ:
    raise RuntimeError("DB_NAME must be set in production.")
if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be configured in production.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", "")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "")

if len(JWT_SIGNING_KEY) < 64:
    raise RuntimeError("JWT_SIGNING_KEY must contain at least 64 characters in production.")
if not JWT_AUDIENCE:
    raise RuntimeError("JWT_AUDIENCE must be configured in production.")
if not JWT_ISSUER:
    raise RuntimeError("JWT_ISSUER must be configured in production.")

SIMPLE_JWT = {
    **SIMPLE_JWT,
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUDIENCE": JWT_AUDIENCE,
    "ISSUER": JWT_ISSUER,
}

if os.getenv("TRUST_PROXY_SSL", "False").lower() in {"true", "1", "t", "yes"}:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    SECURE_PROXY_SSL_HEADER = None
