"""Per-user notification preferences."""

from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    business_enabled = models.BooleanField(default=True)
    marketing_enabled = models.BooleanField(default=False)
    system_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification preference"
        verbose_name_plural = "Notification preferences"

    def __str__(self):
        return f"Notification preferences for {self.user_id}"
