"""Regression tests for receivables mutation policies."""

import pytest

from receivables.policies.recovery_policy import RecoveryPolicy
from users.models import User


@pytest.mark.django_db
def test_recovery_policy_requires_create_permission():
    user = User.objects.create_user(
        username="recovery-policy",
        email="recovery-policy@example.com",
        password="x",
        is_active=True,
    )

    assert RecoveryPolicy.can_create(user) is False


@pytest.mark.django_db
def test_superuser_can_create_recovery():
    user = User.objects.create_superuser(
        username="recovery-policy-superuser",
        email="recovery-policy-superuser@example.com",
        password="x",
    )

    assert RecoveryPolicy.can_create(user) is True
