"""users/tests/test_portfolio_transfer_on_deactivate.py"""
import pytest
from django.contrib.auth import get_user_model

from crm.models import Portfolio
from crm.services.portfolio_services import create_portfolio_for_commercial
from users.services import user_services

User = get_user_model()


@pytest.fixture
def leaving(db):
    return User.objects.create_user(
        username='leaving', email='leaving@example.com', password='x', is_active=True
    )


@pytest.fixture
def successor(db):
    return User.objects.create_user(
        username='successor', email='successor@example.com', password='x', is_active=True
    )


@pytest.mark.django_db
class TestSoftDeleteTransfersPortfolios:
    def test_transfer_portfolios_on_deactivation(self, leaving, successor):
        create_portfolio_for_commercial(leaving)
        create_portfolio_for_commercial(leaving)

        user_services.soft_delete_user(leaving, transfer_to=successor, reason='Depart')

        leaving.refresh_from_db()
        assert leaving.is_active is False
        # Portfolios moved to the successor
        assert Portfolio.objects.filter(commercial=successor).count() == 2
        assert Portfolio.objects.filter(commercial=leaving).count() == 0

    def test_deactivation_without_transfer_keeps_portfolios(self, leaving):
        create_portfolio_for_commercial(leaving)

        user_services.soft_delete_user(leaving)

        leaving.refresh_from_db()
        assert leaving.is_active is False
        # No target given -> portfolios stay with the (now inactive) commercial
        assert Portfolio.objects.filter(commercial=leaving).count() == 1
