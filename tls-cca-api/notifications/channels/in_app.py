"""In-app notification channel."""

from django.utils import timezone

from notifications.models import Notification, NotificationDelivery
from .base import NotificationChannel


class InAppChannel(NotificationChannel):
    name = NotificationDelivery.CHANNEL_IN_APP

    def send(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
        *,
        context=None,
    ) -> None:
        # The notification row is the in-app message itself.  The delivery row
        # only records that the channel has been accepted successfully.
        delivery.attempts += 1
        delivery.status = NotificationDelivery.STATUS_SENT
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=["attempts", "status", "sent_at", "updated_at"])
