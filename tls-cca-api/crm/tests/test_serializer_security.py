"""Serializer-level mass-assignment protections for CRM resources."""

from crm.serializers import CustomerSerializer, PortfolioSerializer


def test_customer_is_active_is_read_only():
    serializer = CustomerSerializer()

    assert serializer.fields["is_active"].read_only is True


def test_portfolio_commercial_is_read_only():
    serializer = PortfolioSerializer()

    assert serializer.fields["commercial"].read_only is True
