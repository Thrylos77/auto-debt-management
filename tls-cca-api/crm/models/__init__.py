"""Public CRM model exports.

The package keeps the historical ``from crm.models import ...`` API stable while
separating customer and portfolio domain models into focused modules.
"""

from .customer import Customer, CustomerAddress, MoralPersonDetail, PhysicalPersonDetail
from .portfolio import Portfolio, PortfolioTransfer, PortfolioTransferQuerySet

__all__ = [
    "Customer",
    "CustomerAddress",
    "MoralPersonDetail",
    "PhysicalPersonDetail",
    "Portfolio",
    "PortfolioTransfer",
    "PortfolioTransferQuerySet",
]
