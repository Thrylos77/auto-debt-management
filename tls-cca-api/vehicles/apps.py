"""Django application configuration for vehicle stock and inventory."""

from django.apps import AppConfig


class VehiclesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vehicles"
    verbose_name = "Vehicles & Inventory"

    def ready(self):
        from . import signals  # noqa: F401
