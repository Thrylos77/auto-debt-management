"""Channel contract used by NotificationService."""

from abc import ABC, abstractmethod

from notifications.models import Notification, NotificationDelivery


class NotificationChannel(ABC):
    """Base interface for synchronous notification delivery."""

    name = ""

    @abstractmethod
    def send(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
        *,
        context=None,
    ) -> None:
        """Deliver one notification and raise on a provider failure."""
