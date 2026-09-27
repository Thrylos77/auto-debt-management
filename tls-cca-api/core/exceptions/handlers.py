"""Normalized DRF exception handler."""

from rest_framework.views import exception_handler as drf_exception_handler

from core.request_context import get_correlation_id


def _error_code(exc) -> str:
    code = getattr(exc, "default_code", None)
    if code:
        return str(code)
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        return "validation_error"
    return "api_error"


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    correlation_id = get_correlation_id()
    data = response.data
    if isinstance(data, dict):
        data.setdefault("code", _error_code(exc))
        if correlation_id:
            data.setdefault("correlation_id", correlation_id)
        response.data = data
    else:
        response.data = {
            "detail": data,
            "code": _error_code(exc),
            **({"correlation_id": correlation_id} if correlation_id else {}),
        }
    return response
