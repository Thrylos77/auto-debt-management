"""crm/tests/test_portfolio_services.py"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from crm.models import Portfolio, PortfolioTransfer
from crm.services.portfolio_services import (
    assign_portfolio,
    create_portfolio_for_commercial,
    transfer_active_portfolios_of_commercial,
    transfer_portfolio,
)

User = get_user_model()


@pytest.fixture
def commercial(db):
    return User.objects.create_user(
        username='commercial1', email='commercial1@example.com', password='x', is_active=True
    )


@pytest.fixture
def target(db):
    return User.objects.create_user(
        username='commercial2', email='commercial2@example.com', password='x', is_active=True
    )


@pytest.fixture
def portfolio(commercial):
    return create_portfolio_for_commercial(commercial)


@pytest.mark.django_db
class TestAssignPortfolio:
    def test_assign_moves_owner_and_logs_journal(self, portfolio, target):
        old_owner_id = portfolio.commercial_id
        result = assign_portfolio(portfolio, target, transferred_by=target, reason='Reaffectation')
        result.refresh_from_db()
        assert result.commercial_id == target.id
        assert result.active is True

        transfer = PortfolioTransfer.objects.get(portfolio=result)
        assert transfer.from_commercial_id == old_owner_id  # old owner
        assert transfer.to_commercial_id == target.id
        assert transfer.transferred_by_id == target.id
        assert transfer.reason == 'Reaffectation'

    def test_assign_rejects_inactive_target(self, portfolio, target):
        target.is_active = False
        target.save()
        with pytest.raises(ValidationError):
            assign_portfolio(portfolio, target)

    def test_assign_rejects_same_owner(self, portfolio, commercial):
        with pytest.raises(ValidationError):
            assign_portfolio(portfolio, commercial)

    def test_assign_activates_inactive_portfolio(self, commercial, target):
        portfolio = Portfolio.objects.create(ref='PF-999', commercial=commercial, active=False)
        result = assign_portfolio(portfolio, target)
        result.refresh_from_db()
        assert result.active is True
        assert result.commercial_id == target.id


@pytest.mark.django_db
class TestTransferPortfolio:
    def test_transfer_redirects_to_assign(self, portfolio, target):
        result = transfer_portfolio(portfolio, target, reason='depart')
        result.refresh_from_db()
        assert result.commercial_id == target.id
        assert PortfolioTransfer.objects.filter(portfolio=result).exists()


@pytest.mark.django_db
class TestTransferActivePortfoliosOfCommercial:
    def test_transfers_all_active_portfolios(self, commercial, target):
        p1 = create_portfolio_for_commercial(commercial)
        p2 = create_portfolio_for_commercial(commercial)
        # An inactive portfolio of the leaving commercial should NOT be transferred
        Portfolio.objects.create(ref='PF-700', commercial=commercial, active=False)

        transferred = transfer_active_portfolios_of_commercial(commercial, target, reason='depart')
        assert len(transferred) == 2  # only active ones
        assert Portfolio.objects.filter(commercial=target, active=True).count() == 2
        assert Portfolio.objects.filter(commercial=commercial).count() == 1  # inactive one stays
        assert PortfolioTransfer.objects.filter(to_commercial=target).count() == 2

    def test_transfers_nothing_if_no_active_portfolios(self, commercial, target):
        transfer_active_portfolios_of_commercial(commercial, target)
        assert PortfolioTransfer.objects.count() == 0

    def test_rejects_inactive_target(self, commercial, target):
        target.is_active = False
        target.save()
        with pytest.raises(ValidationError):
            transfer_active_portfolios_of_commercial(commercial, target)
