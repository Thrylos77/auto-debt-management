"""Append-only audit event model."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("AuditEvent is append-only.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditEvent is append-only.")


class AuditEventManager(models.Manager.from_queryset(AuditEventQuerySet)):
    pass


class AuditEvent(models.Model):
    class Category(models.TextChoices):
        SECURITY = "SECURITY", "Security"
        AUTHENTICATION = "AUTHENTICATION", "Authentication"
        AUTHORIZATION = "AUTHORIZATION", "Authorization"
        ADMINISTRATION = "ADMINISTRATION", "Administration"
        BUSINESS = "BUSINESS", "Business"
        SYSTEM = "SYSTEM", "System"
        DATA = "DATA", "Data"
        COMPLIANCE = "COMPLIANCE", "Compliance"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Denied"

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    category = models.CharField(max_length=32, choices=Category.choices, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, db_index=True)
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    objects = AuditEventManager()

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["category", "occurred_at"], name="audit_cat_time_idx"),
            models.Index(fields=["resource_type", "resource_id"], name="audit_resource_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("AuditEvent is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditEvent is append-only.")
