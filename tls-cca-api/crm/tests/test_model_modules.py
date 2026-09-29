"""Regression tests for the CRM model package split."""

from crm.models import Customer, MoralPersonDetail, PhysicalPersonDetail, Portfolio, PortfolioTransfer
from crm.models.customer import Customer as CustomerModuleCustomer
from crm.models.customer import MoralPersonDetail as CustomerModuleMoralDetail
from crm.models.customer import PhysicalPersonDetail as CustomerModulePhysicalDetail
from crm.models.portfolio import Portfolio as PortfolioModulePortfolio
from crm.models.portfolio import PortfolioTransfer as PortfolioModuleTransfer


def test_customer_models_live_in_customer_module():
    assert Customer is CustomerModuleCustomer
    assert PhysicalPersonDetail is CustomerModulePhysicalDetail
    assert MoralPersonDetail is CustomerModuleMoralDetail


def test_portfolio_models_live_in_portfolio_module():
    assert Portfolio is PortfolioModulePortfolio
    assert PortfolioTransfer is PortfolioModuleTransfer
