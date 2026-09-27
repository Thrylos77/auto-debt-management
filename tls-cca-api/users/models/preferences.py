from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    THEME_CHOICES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference")
    language = models.CharField(max_length=16, default="fr-fr")
    timezone = models.CharField(max_length=64, default="UTC")
    theme = models.CharField(max_length=16, choices=THEME_CHOICES, default="system")
    email_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    session_timeout_minutes = models.PositiveIntegerField(default=60)

    class Meta:
        verbose_name = "User preference"
        verbose_name_plural = "User preferences"

    def __str__(self):
        return f"Preferences for {self.user}"
