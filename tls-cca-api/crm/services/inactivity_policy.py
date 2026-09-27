"""Customer inactivity policy backed by the platform configuration service."""

import calendar
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from configuration.registry import (
    CUSTOMER_INACTIVITY_MONTHS_KEY,
    DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
    MAX_INACTIVITY_MONTHS,
    MIN_INACTIVITY_MONTHS,
)
from configuration.services import ConfigurationService


def get_customer_inactivity_months() -> int:
    """Read the CRM inactivity period from typed platform configuration."""

    return int(
        ConfigurationService.get(
            CUSTOMER_INACTIVITY_MONTHS_KEY,
            default=DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
        )
    )


def set_customer_inactivity_months(
    months,
    *,
    actor=None,
    request=None,
):
    """Validate and persist the CRM inactivity policy through ConfigurationService."""

    try:
        months = int(months)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"inactivity_months": "Must be a valid integer."}) from exc

    if months < MIN_INACTIVITY_MONTHS or months > MAX_INACTIVITY_MONTHS:
        raise ValidationError(
            {
                "inactivity_months": (
                    f"Must be between {MIN_INACTIVITY_MONTHS} and "
                    f"{MAX_INACTIVITY_MONTHS} months."
                )
            }
        )

    return ConfigurationService.set(
        CUSTOMER_INACTIVITY_MONTHS_KEY,
        months,
        actor=actor,
        request=request,
    )


def subtract_months(dt: datetime, months: int) -> datetime:
    """Subtract calendar months while clamping to the destination month end."""

    total_months = dt.year * 12 + (dt.month - 1) - months
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def get_customer_inactivity_threshold() -> datetime:
    """Return the current inactivity threshold used by the CRM service."""

    return subtract_months(
        timezone.now(),
        get_customer_inactivity_months(),
    )
