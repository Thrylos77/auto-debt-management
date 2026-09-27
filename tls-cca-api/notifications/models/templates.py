"""Optional database-backed notification templates."""

from django.db import models


class NotificationTemplate(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_IN_APP = "in_app"

    CHANNEL_CHOICES = (
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_IN_APP, "In app"),
    )

    code = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=20)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code
