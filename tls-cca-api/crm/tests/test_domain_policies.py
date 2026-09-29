"""Regression tests for CRM mutation policies."""

import pytest
from rest_framework.exceptions import PermissionDenied

from crm.models import Portfolio
from crm.services.portfolio_services import assign_portfolio
from rbac.models import Permission, Role, RoleAssignment
from users.models import User


def _grant(user, code):
    role, _ = Role.objects.get_or_create(name=f"POLICY_{code.replace('.', '_')}_{user.pk}")
    permission, _ = Permission.objects.get_or_create(code=code, label=code)
    role.permissions.add(permission)
    RoleAssignment.objects.create(user=user, role=role)


@pytest.mark.django_db
def test_portfolio_assignment_requires_domain_permission():
    actor = User.objects.create_user(
        username="portfolio-policy-actor",
        email="portfolio-policy-actor@example.com",
        password="x",
        is_active=True,
    )
    target = User.objects.create_user(
        username="portfolio-policy-target",
        email="portfolio-policy-target@example.com",
        password="x",
        is_active=True,
    )
    portfolio = Portfolio.objects.create(
        ref="PF_POLICY",
        commercial=actor,
    )

    with pytest.raises(PermissionDenied):
        assign_portfolio(
            portfolio,
            target,
            transferred_by=actor,
        )


def test_portfolio_assignment_policy_accepts_authorized_target(db):
    actor = User.objects.create_user(
        username="portfolio-policy-authorized",
        email="portfolio-policy-authorized@example.com",
        password="x",
        is_active=True,
    )
    target = User.objects.create_user(
        username="portfolio-policy-authorized-target",
        email="portfolio-policy-authorized-target@example.com",
        password="x",
        is_active=True,
    )
    _grant(actor, "portfolio.assign")

    portfolio = Portfolio.objects.create(
        ref="PF_POLICY_OK",
        commercial=target,
    )

    result = assign_portfolio(
        portfolio,
        actor,
        transferred_by=actor,
    )

    assert result.commercial_id == actor.id


@pytest.mark.django_db
def test_customer_timeline_policy_requires_permission_and_scope():
    from crm.models import Customer, Portfolio
    from crm.policies.customer_policy import CustomerPolicy

    owner = User.objects.create_user(
        username="timeline-policy-owner",
        email="timeline-policy-owner@example.com",
        password="x",
        is_active=True,
    )
    viewer = User.objects.create_user(
        username="timeline-policy-viewer",
        email="timeline-policy-viewer@example.com",
        password="x",
        is_active=True,
    )
    portfolio = Portfolio.objects.create(
        ref="PF_TIMELINE_POLICY",
        commercial=owner,
    )
    customer = Customer.objects.create(
        phone="1234567890",
        portfolio=portfolio,
    )

    assert CustomerPolicy.can_view_timeline(viewer, customer) is False

    _grant(viewer, "customer.timeline")
    assert CustomerPolicy.can_view_timeline(viewer, customer) is False
    assert CustomerPolicy.can_view_timeline(owner, customer) is False

    _grant(owner, "customer.timeline")
    assert CustomerPolicy.can_view_timeline(owner, customer) is True
