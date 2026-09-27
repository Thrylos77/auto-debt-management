"""Import-boundary regression tests for platform modules."""

from pathlib import Path


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
