"""Regression tests for credit-sale service policies."""

import pytest

from sales.models import CreditSaleStatus
from sales.policies.credit_sale_policy import CreditSalePolicy
from users.models import User


class _Sale:
    def __init__(self, commercial_id):
        self.commercial_id = commercial_id


@pytest.mark.django_db
def test_credit_sale_policy_blocks_own_approval():
    user = User.objects.create_user(
        username="sale-policy",
        email="sale-policy@example.com",
        password="x",
        is_active=True,
    )
    sale = _Sale(user.id)

    assert CreditSalePolicy.can_change_status(
        user,
        sale,
        CreditSaleStatus.APPROVED,
    ) is False
