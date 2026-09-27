"""Declarative definitions for supported application settings."""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class SettingDefinition:
    """Describes how one configuration key is stored, validated and exposed."""

    key: str
    default: Any
    value_type: str
    category: str
    is_public: bool = False
    scope: str = "GLOBAL"
    description: str = ""
    validator: Callable[[Any], Any] | None = None


CUSTOMER_INACTIVITY_MONTHS_KEY = "customer_inactivity_duration_months"
DEFAULT_CUSTOMER_INACTIVITY_MONTHS = 48
MIN_INACTIVITY_MONTHS = 1
MAX_INACTIVITY_MONTHS = 600


def _validate_customer_inactivity_months(value: Any) -> int:
    """Validate the CRM inactivity period while keeping configuration generic."""

    try:
        months = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("The inactivity duration must be an integer.") from exc

    if months < MIN_INACTIVITY_MONTHS or months > MAX_INACTIVITY_MONTHS:
        raise ValueError(
            "The inactivity duration must be between "
            f"{MIN_INACTIVITY_MONTHS} and {MAX_INACTIVITY_MONTHS} months."
        )

    return months


SETTING_DEFINITIONS = {
    CUSTOMER_INACTIVITY_MONTHS_KEY: SettingDefinition(
        key=CUSTOMER_INACTIVITY_MONTHS_KEY,
        default=DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
        value_type="INTEGER",
        category="CRM",
        description=(
            "Number of months after which an inactive customer can be "
            "automatically deactivated."
        ),
        validator=_validate_customer_inactivity_months,
    ),
}


def get_setting_definition(key: str) -> SettingDefinition | None:
    """Return a definition by key without raising for an unknown setting."""

    return SETTING_DEFINITIONS.get(key)
