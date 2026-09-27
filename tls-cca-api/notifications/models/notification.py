"""Persistent in-app notifications."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    SECURITY = "SECURITY"
    BUSINESS = "BUSINESS"
    MARKETING = "MARKETING"
    SYSTEM = "SYSTEM"

    CATEGORY_CHOICES = (
        (SECURITY, "Security"),
        (BUSINESS, "Business"),
        (MARKETING, "Marketing"),
        (SYSTEM, "System"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    code = models.CharField(max_length=120)
    title = models.CharField(max_length=255)
    message = models.TextField()
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=150, blank=True)
    data = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=150, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="notif_user_read_created_idx",
            ),
            models.Index(
                fields=["user", "category", "created_at"],
                name="notif_user_cat_created_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="notif_user_idempotency_uq",
            ),
        ]

    def __str__(self):
        return f"{self.code} for {self.user_id}"
