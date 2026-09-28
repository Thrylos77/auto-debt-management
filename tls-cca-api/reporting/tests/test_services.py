"""Regression tests for reporting-owned query services."""

import pytest

from reporting.services.search_services import search_global


@pytest.mark.django_db
def test_global_search_returns_empty_payload_for_short_query(new_user):
    assert search_global(new_user, "a") == {
        "sales": [],
        "debts": [],
        "customers": [],
    }
