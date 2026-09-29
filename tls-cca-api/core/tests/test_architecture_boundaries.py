"""Import-boundary and platform ownership regression tests."""

from pathlib import Path

import pytest
from django.test import Client


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_users_no_longer_depends_on_legacy_core_settings_service():
    users_root = PROJECT_ROOT / "users"
    forbidden = "core.services.settings_services"

    for path in users_root.rglob("*.py"):
        assert forbidden not in _read(str(path.relative_to(PROJECT_ROOT)))


def test_crm_reads_configuration_through_its_domain_adapter():
    customer_service = _read("crm/services/customer_services.py")
    inactivity_service = _read("crm/services/inactivity_policy.py")

    assert "core.services.settings_services" not in customer_service
    assert "ConfigurationService" in inactivity_service


def test_notifications_does_not_import_business_apps():
    notifications_root = PROJECT_ROOT / "notifications"
    forbidden_modules = (
        "crm",
        "sales",
        "receivables",
        "reporting",
    )

    for path in notifications_root.rglob("*.py"):
        content = _read(str(path.relative_to(PROJECT_ROOT)))
        for module_name in forbidden_modules:
            assert f"{module_name}." not in content
            assert f"from {module_name} " not in content
            assert f"import {module_name}" not in content


def test_core_does_not_import_business_modules():
    """Core must remain independent from business applications."""

    forbidden_modules = (
        "crm",
        "sales",
        "receivables",
        "reporting",
        "users",
    )

    for path in (PROJECT_ROOT / "core").rglob("*.py"):
        if "tests" in path.parts:
            continue
        content = _read(str(path.relative_to(PROJECT_ROOT)))
        for module_name in forbidden_modules:
            assert f"from {module_name} " not in content
            assert f"from {module_name}." not in content
            assert f"import {module_name}" not in content


def test_reporting_owns_former_core_global_query_services():
    assert (PROJECT_ROOT / "reporting/services/dashboard_services.py").exists()
    assert (PROJECT_ROOT / "reporting/services/search_services.py").exists()
    assert not (PROJECT_ROOT / "core/services/stats_services.py").exists()
    assert not (PROJECT_ROOT / "core/services/search_services.py").exists()


def test_internal_events_are_owned_by_core():
    assert (PROJECT_ROOT / "core/events.py").exists()
    assert not (PROJECT_ROOT / "users/events.py").exists()


def test_final_cleanup_has_no_legacy_api_modules_or_adapters():
    forbidden_paths = (
        "config/schema.py",
        "users/legacy_urls.py",
        "reporting/legacy_urls.py",
        "users/views/views.py",
        "users/views/views_2fa.py",
        "users/services/user_services.py",
        "users/services/otp_service.py",
        "users/models/otp.py",
        "users/models/recovery.py",
        "users/policies/twofa_policy.py",
        "users/services/twofa_services.py",
        "rbac/services/permission_services.py",
        "rbac/management/commands/backfill_legacy_rbac.py",
        "rbac/management/commands/seed_rbac_v2.py",
        "users/management/commands/migrate_legacy_2fa.py",
        "configuration/management/commands/migrate_legacy_settings.py",
        "rbac/signals.py",
    )

    for relative_path in forbidden_paths:
        assert not (PROJECT_ROOT / relative_path).exists(), relative_path


def test_config_exposes_only_versioned_application_routes():
    config_urls = _read("config/urls.py")

    legacy_markers = (
        'include("users.legacy_urls")',
        'include("reporting.legacy_urls")',
        'include("rbac.urls")',
        'path("api/crm/"',
        'path("api/sales/"',
        'path("api/receivables/"',
        'path("api/reporting/"',
        'path("api/audit/"',
        'path("api/token/"',
    )

    for marker in legacy_markers:
        assert marker not in config_urls


@pytest.mark.parametrize(
    "path",
    [
        "/api/core/dashboard/summary/",
        "/api/users/",
        "/api/permissions/",
        "/api/roles/",
        "/api/groups/",
        "/api/crm/",
        "/api/sales/",
        "/api/receivables/",
        "/api/reporting/",
        "/api/audit/",
        "/api/token/",
    ],
)
def test_legacy_api_prefixes_are_unroutable(path):
    """The removed API prefixes must return 404 rather than a compatibility response."""
    response = Client().get(path)
    assert response.status_code == 404


def test_user_deactivation_source_has_no_legacy_transfer_alias():
    source = _read("users/views/users.py")
    assert 'request.data.get("transfer_to")' not in source
    assert 'request.data.get("successor_user_id")' in source
