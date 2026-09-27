"""Configuration service and API regression tests."""

import pytest

from audit.models import AuditEvent
from configuration.models import SystemSetting
from configuration.registry import (
    CUSTOMER_INACTIVITY_MONTHS_KEY,
    DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
)
from configuration.services import ConfigurationService, ConfigurationTypeCodec


@pytest.mark.django_db(transaction=True)
class TestConfigurationService:
    def test_registered_setting_uses_registry_default(self):
        assert (
            ConfigurationService.get(CUSTOMER_INACTIVITY_MONTHS_KEY)
            == DEFAULT_CUSTOMER_INACTIVITY_MONTHS
        )

    def test_set_round_trip_keeps_typed_integer(self):
        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            36,
        )

        assert ConfigurationService.get(CUSTOMER_INACTIVITY_MONTHS_KEY) == 36
        setting = SystemSetting.objects.get(key=CUSTOMER_INACTIVITY_MONTHS_KEY)
        assert setting.value == "36"
        assert setting.value_type == "INTEGER"

    def test_configuration_write_does_not_store_secret_value_in_audit(self):
        from users.models import User

        user = User.objects.create_superuser(
            username="config-audit",
            email="config-audit@example.com",
            password="ValidPass123!",
        )

        # The audit is written in the same transaction as the configuration change.
        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            36,
            actor=user,
        )

        event = AuditEvent.objects.filter(
            action="configuration.set",
            actor_user=user,
        ).order_by("-id").first()

        assert event is not None
        assert "value" not in event.metadata
        assert event.metadata["key"] == CUSTOMER_INACTIVITY_MONTHS_KEY
        assert event.metadata["value_type"] == "INTEGER"

    def test_invalid_customer_inactivity_value_is_rejected(self):
        with pytest.raises(Exception):
            ConfigurationService.set(
                CUSTOMER_INACTIVITY_MONTHS_KEY,
                0,
            )

    def test_optional_metadata_is_preserved_when_not_supplied(self):
        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            36,
            description="Custom description",
            is_public=True,
        )

        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            24,
        )

        setting = SystemSetting.objects.get(key=CUSTOMER_INACTIVITY_MONTHS_KEY)

        assert setting.value == "24"
        assert setting.description == "Custom description"
        assert setting.is_public is True

    def test_repeated_global_updates_keep_one_setting_row(self):
        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            36,
        )
        ConfigurationService.set(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            24,
        )

        assert SystemSetting.objects.filter(
            key=CUSTOMER_INACTIVITY_MONTHS_KEY,
            scope="GLOBAL",
            scope_ref="",
        ).count() == 1


class TestConfigurationTypeCodec:
    def test_boolean_round_trip(self):
        assert ConfigurationTypeCodec.decode(
            ConfigurationTypeCodec.encode(True, "BOOLEAN"),
            "BOOLEAN",
        ) is True

    def test_json_round_trip(self):
        value = {"enabled": True, "limits": [1, 2, 3]}
        encoded = ConfigurationTypeCodec.encode(value, "JSON")
        assert ConfigurationTypeCodec.decode(encoded, "JSON") == value

    def test_duration_accepts_human_suffix(self):
        assert ConfigurationTypeCodec.encode("2h", "DURATION") == "7200"
