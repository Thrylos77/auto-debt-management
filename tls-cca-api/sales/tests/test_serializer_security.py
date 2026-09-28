"""Serializer-level mass-assignment protections for sales resources."""

from sales.serializers import CreditSaleSerializer


def test_credit_sale_controlled_fields_are_read_only():
    serializer = CreditSaleSerializer()

    assert serializer.fields["commercial"].read_only is True
    assert serializer.fields["portfolio"].read_only is True
    assert serializer.fields["status"].read_only is True
