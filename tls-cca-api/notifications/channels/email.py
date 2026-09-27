"""SMTP email channel for notifications."""

from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationTemplate,
)
from .base import NotificationChannel


DEFAULT_EMAIL_SUBJECTS = {
    "password_reset_otp": "Your One-Time Password (OTP) for Password Reset",
}


class EmailChannel(NotificationChannel):
    name = NotificationDelivery.CHANNEL_EMAIL

    def send(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
        *,
        context=None,
    ) -> None:
        delivery.attempts += 1
        delivery.save(
            update_fields=[
                "attempts",
                "updated_at",
            ]
        )

        try:
            template_code = notification.code
            db_template = NotificationTemplate.objects.filter(
                code=template_code,
                channel=NotificationDelivery.CHANNEL_EMAIL,
                is_active=True,
            ).first()

            render_context = {
                "notification": notification,
                **(context or {}),
            }

            if db_template is not None:
                html_message = Template(db_template.body_template).render(
                    Context(render_context)
                )
                subject = db_template.subject or notification.title
            else:
                template_name = (
                    f"notifications/emails/{template_code}.html"
                )
                html_message = render_to_string(template_name, render_context)
                subject = DEFAULT_EMAIL_SUBJECTS.get(
                    template_code,
                    notification.title,
                )

            send_mail(
                subject,
                strip_tags(html_message),
                settings.DEFAULT_FROM_EMAIL,
                [notification.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as exc:
            delivery.status = NotificationDelivery.STATUS_FAILED
            delivery.error_message = str(exc)[:2000]
            delivery.save(
                update_fields=[
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )
            raise

        delivery.status = NotificationDelivery.STATUS_SENT
        delivery.sent_at = timezone.now()
        delivery.save(
            update_fields=[
                "status",
                "sent_at",
                "updated_at",
            ]
        )
