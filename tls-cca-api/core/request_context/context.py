"""Request-scoped context built on ContextVar."""

from contextvars import ContextVar
from typing import Optional


_correlation_id: ContextVar[Optional[str]] = ContextVar("tls_cca_correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def set_correlation_id(value: Optional[str]):
    return _correlation_id.set(value)


def reset_correlation_id(token) -> None:
    _correlation_id.reset(token)
