"""Public registry API for application configuration definitions."""

from .definitions import (
    CUSTOMER_INACTIVITY_MONTHS_KEY,
    DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
    MAX_INACTIVITY_MONTHS,
    MIN_INACTIVITY_MONTHS,
    SETTING_DEFINITIONS,
    SettingDefinition,
    get_setting_definition,
)


__all__ = [
    "CUSTOMER_INACTIVITY_MONTHS_KEY",
    "DEFAULT_CUSTOMER_INACTIVITY_MONTHS",
    "MAX_INACTIVITY_MONTHS",
    "MIN_INACTIVITY_MONTHS",
    "SETTING_DEFINITIONS",
    "SettingDefinition",
    "get_setting_definition",
]
