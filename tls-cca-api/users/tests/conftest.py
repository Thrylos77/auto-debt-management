"""Fixtures shared by the users application tests."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Prevent sensitive-operation throttle state from leaking between tests."""
    cache.clear()
    yield
    cache.clear()
