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


VEHICLE_RESERVATION_DEFAULT_DURATION_KEY = "vehicles.reservation.default_duration_hours"
DEFAULT_VEHICLE_RESERVATION_DURATION_HOURS = 72
VEHICLE_IMAGE_MAX_SIZE_KEY = "vehicles.image.max_size_bytes"
DEFAULT_VEHICLE_IMAGE_MAX_SIZE_BYTES = 5 * 1024 * 1024


def _validate_reservation_duration_hours(value: Any) -> int:
    try:
        hours = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("The reservation duration must be an integer number of hours.") from exc
    if hours < 1 or hours > 720:
        raise ValueError("The reservation duration must be between 1 and 720 hours.")
    return hours


def _validate_vehicle_image_max_size(value: Any) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("The image size limit must be an integer number of bytes.") from exc
    if size < 256 * 1024 or size > 20 * 1024 * 1024:
        raise ValueError("The image size limit must be between 256 KiB and 20 MiB.")
    return size


SETTING_DEFINITIONS.update(
    {
        VEHICLE_RESERVATION_DEFAULT_DURATION_KEY: SettingDefinition(
            key=VEHICLE_RESERVATION_DEFAULT_DURATION_KEY,
            default=DEFAULT_VEHICLE_RESERVATION_DURATION_HOURS,
            value_type="INTEGER",
            category="VEHICLES",
            description="Default duration for a vehicle reservation in hours.",
            validator=_validate_reservation_duration_hours,
        ),
        VEHICLE_IMAGE_MAX_SIZE_KEY: SettingDefinition(
            key=VEHICLE_IMAGE_MAX_SIZE_KEY,
            default=DEFAULT_VEHICLE_IMAGE_MAX_SIZE_BYTES,
            value_type="INTEGER",
            category="VEHICLES",
            description="Maximum allowed size for a vehicle image in bytes.",
            validator=_validate_vehicle_image_max_size,
        ),
    }
)
