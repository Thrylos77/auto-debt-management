""" core/services/settings_services.py

Typed helpers around the generic `SystemSetting` key/value store, focused on the
customer inactivity auto-deactivation policy (in months).
"""

import calendar
import logging
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import SystemSetting

logger = logging.getLogger(__name__)

# --- Keys & defaults ---
CUSTOMER_INACTIVITY_MONTHS_KEY = "customer_inactivity_duration_months"
DEFAULT_CUSTOMER_INACTIVITY_MONTHS = 48  # default policy: 4 years

MIN_INACTIVITY_MONTHS = 1
MAX_INACTIVITY_MONTHS = 600


def get_setting(key: str, default=None):
    """Returns the raw string value for a setting, or `default` if absent/empty."""
    try:
        setting = SystemSetting.objects.get(key=key)
    except SystemSetting.DoesNotExist:
        return default
    return setting.value if setting.value not in (None, "") else default


def set_setting(key: str, value: str) -> SystemSetting:
    """Creates or updates a setting with a string value."""
    setting, _ = SystemSetting.objects.update_or_create(key=key, defaults={"value": str(value)})
    return setting


def get_customer_inactivity_months() -> int:
    """Returns the configured inactivity duration in months (default: 48)."""
    raw = get_setting(CUSTOMER_INACTIVITY_MONTHS_KEY)
    if raw is None:
        return DEFAULT_CUSTOMER_INACTIVITY_MONTHS
    try:
        months = int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid customer inactivity months '%s'; using default.", raw)
        return DEFAULT_CUSTOMER_INACTIVITY_MONTHS
    return months


def set_customer_inactivity_months(months) -> SystemSetting:
    """Validates and stores the inactivity duration (in months)."""
    try:
        months = int(months)
    except (TypeError, ValueError):
        raise ValidationError({"inactivity_months": "Must be a valid integer."})
    if months < MIN_INACTIVITY_MONTHS or months > MAX_INACTIVITY_MONTHS:
        raise ValidationError({
            "inactivity_months": (
                f"Must be between {MIN_INACTIVITY_MONTHS} and "
                f"{MAX_INACTIVITY_MONTHS} months."
            )
        })
    return set_setting(CUSTOMER_INACTIVITY_MONTHS_KEY, months)


def subtract_months(dt: datetime, months: int) -> datetime:
    """
    Returns `dt` minus `months` months, clamping the day to the last valid day of
    the resulting month (calendar-accurate, e.g. May 31 - 1 month = Apr 30).
    """
    total_months = dt.year * 12 + (dt.month - 1) - months
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def get_customer_inactivity_threshold() -> datetime:
    """
    Returns the aware datetime (now - configured months) before which a customer
    is considered inactive for auto-deactivation purposes.
    """
    return subtract_months(timezone.now(), get_customer_inactivity_months())
