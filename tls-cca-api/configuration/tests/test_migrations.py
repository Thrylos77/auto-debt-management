"""Migration-chain regression tests for Configuration and legacy Core data."""

import importlib

import pytest

from configuration.models import SystemSetting


@pytest.mark.django_db
def test_global_scope_reference_is_normalized_to_empty_string():
    field = SystemSetting._meta.get_field("scope_ref")

    assert field.null is False
    assert field.default == ""


def test_legacy_copy_migration_runs_before_core_setting_removal():
    legacy_migration = importlib.import_module(
        "configuration.migrations.0004_migrate_legacy_systemsetting"
    )
    core_migration = importlib.import_module(
        "core.migrations.0002_remove_systemsetting"
    )

    assert ("core", "0001_initial") in legacy_migration.Migration.dependencies
    assert (
        "configuration",
        "0004_migrate_legacy_systemsetting",
    ) in core_migration.Migration.dependencies
