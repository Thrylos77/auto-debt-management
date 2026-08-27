"""core/tests/test_settings.py"""
import pytest
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import SystemSetting
from core.services import settings_services


@pytest.mark.django_db
class TestCustomerInactivityMonths:
    def test_default_is_48_months(self):
        assert settings_services.get_customer_inactivity_months() == 48

    def test_set_and_get_months(self):
        settings_services.set_customer_inactivity_months(24)
        assert settings_services.get_customer_inactivity_months() == 24
        assert SystemSetting.objects.filter(
            key=settings_services.CUSTOMER_INACTIVITY_MONTHS_KEY
        ).exists()

    def test_set_rejects_invalid_values(self):
        with pytest.raises(ValidationError):
            settings_services.set_customer_inactivity_months(0)
        with pytest.raises(ValidationError):
            settings_services.set_customer_inactivity_months(9999)
        with pytest.raises(ValidationError):
            settings_services.set_customer_inactivity_months("not-a-number")


@pytest.mark.django_db
class TestSubtractMonths:
    def test_subtract_months_simple(self):
        dt = datetime(2024, 6, 15, 10, 30)
        result = settings_services.subtract_months(dt, 6)
        assert result == datetime(2023, 12, 15, 10, 30)

    def test_subtract_months_clamps_to_last_day(self):
        dt = datetime(2024, 3, 31, 12, 0)  # Mar 31
        result = settings_services.subtract_months(dt, 1)  # Feb
        assert result == datetime(2024, 2, 29, 12, 0)  # leap year

    def test_subtract_months_crosses_year(self):
        dt = datetime(2024, 2, 15, 12, 0)
        result = settings_services.subtract_months(dt, 3)
        assert result == datetime(2023, 11, 15, 12, 0)

    def test_threshold_is_aware_and_in_past(self):
        t = settings_services.get_customer_inactivity_threshold()
        assert timezone.is_aware(t)
        assert t < timezone.now()
