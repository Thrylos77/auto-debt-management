"""Delivery journal for notification channels."""

from django.db import models

from .notification import Notification


class NotificationDelivery(models.Model):
    CHANNEL_IN_APP = "in_app"
    CHANNEL_EMAIL = "email"

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    CHANNEL_CHOICES = (
        (CHANNEL_IN_APP, "In app"),
        (CHANNEL_EMAIL, "Email"),
    )
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    attempts = models.PositiveIntegerField(default=0)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel"],
                name="notif_delivery_notification_channel_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["channel", "status", "created_at"],
                name="notif_delivery_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.notification_id}:{self.channel}:{self.status}"
