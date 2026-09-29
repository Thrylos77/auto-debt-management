"""Common TLS CCA settings.

Environment-specific modules override only what needs to differ.
"""

import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-this-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in {"true", "1", "t", "yes"}
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]


def _env_list(name: str) -> list[str]:
    """Read a comma-separated environment variable into a clean list."""
    return [
        value.strip()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    ]


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable with an explicit default."""
    return os.getenv(name, str(default)).lower() in {"true", "1", "t", "yes"}

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.correlation.CorrelationIdMiddleware",
    "core.middleware.request_limits.RequestBodySizeLimitMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "simple_history",
    "core.apps.CoreConfig",
    "users.apps.UsersConfig",
    "rbac.apps.RbacConfig",
    "audit.apps.AuditConfig",
    "configuration.apps.ConfigurationConfig",
    "notifications.apps.NotificationsConfig",
    "sales.apps.SalesConfig",
    "crm.apps.CrmConfig",
    "receivables.apps.ReceivablesConfig",
    "reporting.apps.ReportingConfig",
]

DB_NAME = os.getenv("DB_NAME")
if DB_NAME:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {
        "NAME": "users.utils.RegexPasswordValidator",
        "OPTIONS": {
            "pattern": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).+$",
            "message": "Password must contain uppercase, lowercase, digit, and special character.",
        },
    },
]

LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "fr-fr")
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "users.authentication.EnforcedJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "core.exceptions.handlers.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "5/minute",
        "twofa": "5/minute",
        "password_reset": "5/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TLS CCA API",
    "DESCRIPTION": "Versioned API backend for the CCA application.",
    "VERSION": "2.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Two models expose a field named ``status`` with different choices.
    # Naming those enums explicitly avoids Status/Status001 collisions in the
    # generated schema.
    "ENUM_NAME_OVERRIDES": {
        "CreditSaleStatusEnum": [
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        "AuditEventStatusEnum": [
            ("success", "Success"),
            ("failure", "Failure"),
            ("denied", "Denied"),
        ],
    },
}

JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", "")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE") or None
JWT_ISSUER = os.getenv("JWT_ISSUER") or None

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    # Production overrides this with a dedicated signing key. Keeping the
    # fallback here preserves local development without hiding the setting.
    "SIGNING_KEY": JWT_SIGNING_KEY or SECRET_KEY,
    "AUDIENCE": JWT_AUDIENCE,
    "ISSUER": JWT_ISSUER,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "JTI_CLAIM": "jti",
    "CHECK_REVOKE_TOKEN": True,
    "REVOKE_TOKEN_CLAIM": "prv",
    "CHECK_USER_IS_ACTIVE": True,
}

TOTP_ISSUER = os.getenv("TOTP_ISSUER", "TLS CCA")
TOTP_ENCRYPTION_KEY = os.getenv("TOTP_ENCRYPTION_KEY", "")

AUTH_PUBLIC_BASE_URL = os.getenv("AUTH_PUBLIC_BASE_URL", "http://localhost:3000")
AUTH_INVITATION_PATH = os.getenv("AUTH_INVITATION_PATH", "/auth/invitation")
AUTH_PASSWORD_RESET_PATH = os.getenv("AUTH_PASSWORD_RESET_PATH", "/auth/password/reset")
AUTH_TWOFA_RECOVERY_PATH = os.getenv("AUTH_TWOFA_RECOVERY_PATH", "/auth/2fa/recovery")

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in {"true", "1", "t", "yes"}
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@tls-cca.local")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

# Explicit API/resource limits complement Django's own request parsing guards.
API_MAX_REQUEST_BYTES = int(os.getenv("API_MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = API_MAX_REQUEST_BYTES
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("DATA_UPLOAD_MAX_NUMBER_FIELDS", "1000"))
DATA_UPLOAD_MAX_NUMBER_FILES = int(os.getenv("DATA_UPLOAD_MAX_NUMBER_FILES", "100"))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024)))

# CORS stays deny-by-default. Origins must be explicitly configured.
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = _env_bool("CORS_ALLOW_ALL_ORIGINS", False)
CORS_ALLOW_CREDENTIALS = _env_bool("CORS_ALLOW_CREDENTIALS", False)
CORS_URLS_REGEX = r"^/api(?:/|$)"
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation": {"()": "core.logging.filters.CorrelationIdFilter"},
    },
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "filters": ["correlation"], "formatter": "standard"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
        "tls_cca": {"handlers": ["console"], "level": os.getenv("APP_LOG_LEVEL", "INFO"), "propagate": False},
    },
}
