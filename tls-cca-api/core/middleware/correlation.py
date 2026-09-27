"""Correlation ID middleware for API and service observability."""

import re
import uuid

from core.request_context import reset_correlation_id, set_correlation_id

_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def _normalize(value: str | None) -> str:
    value = (value or "").strip()
    if value and _SAFE_CORRELATION_ID.fullmatch(value):
        return value
    return str(uuid.uuid4())


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = _normalize(request.headers.get("X-Correlation-ID"))
        token = set_correlation_id(correlation_id)
        request.correlation_id = correlation_id
        try:
            response = self.get_response(request)
        finally:
            reset_correlation_id(token)
        response["X-Correlation-ID"] = correlation_id
        return response
