""" core/models.py """

from django.db import models


class SystemSetting(models.Model):
    """
    A generic key/value store for system-wide, admin-configurable settings
    (e.g. the customer inactivity auto-deactivation policy in months).
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System setting"
        verbose_name_plural = "System settings"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value}"

