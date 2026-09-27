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
