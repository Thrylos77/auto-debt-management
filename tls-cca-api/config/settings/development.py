"""Development settings overlay."""

import os

from .base import *  # noqa: F401,F403

DEBUG = True
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
