"""Shared helpers for translating domain-service errors into API errors."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError


def run_service(service, *args, **kwargs):
    """Execute a domain service and translate its framework-neutral errors for DRF."""
    try:
        return service(*args, **kwargs)
    except PermissionError as exc:
        raise PermissionDenied(str(exc)) from exc
    except DjangoValidationError as exc:
        if getattr(exc, "message_dict", None):
            raise ValidationError(exc.message_dict) from exc
        raise ValidationError(exc.messages or [str(exc)]) from exc
