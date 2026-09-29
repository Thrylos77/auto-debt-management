"""Opaque token helpers used by security-sensitive account flows."""

import hashlib
import secrets


def generate_token() -> str:
    """Return a cryptographically random, URL-safe token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash an opaque token before it is persisted."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
