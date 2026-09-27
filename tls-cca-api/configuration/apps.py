"""Django application configuration for the platform configuration service."""

from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "configuration"
    verbose_name = "Platform configuration"
