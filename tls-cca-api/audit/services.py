"""Audit recording and recursive sensitive-data sanitization."""

import re
from collections.abc import Mapping

from django.db import transaction

from core.request_context import get_correlation_id

from .models import AuditEvent

_SENSITIVE = re.compile(
    r"password|token|secret|otp|authorization|cookie|refresh",
    re.I,
)


def sanitize(value):
    """Redact sensitive values recursively before storing audit metadata."""
    if isinstance(value, Mapping):
        return {
            key: "[REDACTED]"
            if _SENSITIVE.search(str(key))
            else sanitize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]

    return value


class AuditService:
    @staticmethod
    def record(
        *,
        actor=None,
        category,
        action,
        resource=None,
        status="success",
        reason="",
        request=None,
        metadata=None,
    ):
        """Persist an audit event immediately."""
        ip_address = None
        user_agent = ""

        if request is not None:
            forwarded = request.headers.get("X-Forwarded-For", "")
            ip_address = (
                forwarded.split(",")[0].strip()
                if forwarded
                else request.META.get("REMOTE_ADDR")
            )
            user_agent = request.headers.get("User-Agent", "")[:2000]

        return AuditEvent.objects.create(
            actor_user=actor if getattr(actor, "pk", None) else None,
            category=category,
            action=action,
            resource_type=(
                resource.__class__.__name__
                if resource is not None
                else ""
            ),
            resource_id=(
                str(getattr(resource, "pk", ""))
                if resource is not None
                else ""
            ),
            status=status,
            reason=reason or "",
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=(
                get_correlation_id()
                or getattr(request, "correlation_id", "")
                or ""
            ),
            metadata=sanitize(metadata or {}),
        )

    @staticmethod
    def record_on_commit(
        *,
        actor=None,
        category,
        action,
        resource=None,
        status="success",
        reason="",
        request=None,
        metadata=None,
    ):
        """Persist an audit event only after the surrounding transaction commits."""
        transaction.on_commit(
            lambda: AuditService.record(
                actor=actor,
                category=category,
                action=action,
                resource=resource,
                status=status,
                reason=reason,
                request=request,
                metadata=metadata,
            )
        )
