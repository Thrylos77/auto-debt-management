"""Customer timeline aggregation and scope tests."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from audit.models import AuditEvent
from crm.models import Customer, Portfolio
from rbac.models import Permission, Role, RoleAssignment
from receivables.models import Debt, Recovery, Term
from sales.models import CreditSale

User = get_user_model()


def grant(user, *codes):
    role, _ = Role.objects.get_or_create(name=f"V6_TIMELINE_{user.pk}")
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, label=code)
        role.permissions.add(permission)
    RoleAssignment.objects.get_or_create(user=user, role=role)


@pytest.mark.django_db
def test_timeline_aggregates_customer_portfolio_sale_and_recovery_events():
    actor = User.objects.create_user(
        username="v6-timeline-actor",
        email="v6-timeline-actor@example.com",
        password="x",
        is_active=True,
    )
    actor.is_superuser = True
    actor.save(update_fields=["is_superuser"])
    portfolio = Portfolio.objects.create(
        ref="PF-V6-TIMELINE",
        commercial=actor,
        active=True,
    )
    customer = Customer.objects.create(
        email="timeline@example.com",
        phone="+24106000003",
        portfolio=portfolio,
    )

    sale = CreditSale.objects.create(
        customer=customer,
        commercial=actor,
        portfolio=portfolio,
        total_amount=100,
        deposit=0,
        month_duration=1,
    )
    debt = Debt.objects.create(
        sale=sale,
        init_amount=100,
        balance=100,
        month_duration=1,
        regulation_mode="TEST",
    )
    term = Term.objects.create(
        debt=debt,
        term_date=date.today(),
        except_amount=100,
    )
    recovery = Recovery.objects.create(
        term=term,
        commercial=actor,
        amount=25,
        payment_mode="cash",
    )

    AuditEvent.objects.bulk_create([
        AuditEvent(
            actor_user=actor,
            category="BUSINESS",
            action="customer.lifecycle_changed",
            resource_type="Customer",
            resource_id=str(customer.id),
            status="success",
        ),
        AuditEvent(
            actor_user=actor,
            category="ADMINISTRATION",
            action="portfolio.transfer",
            resource_type="Portfolio",
            resource_id=str(portfolio.id),
            status="success",
        ),
        AuditEvent(
            actor_user=actor,
            category="BUSINESS",
            action="creditsale.status_change",
            resource_type="CreditSale",
            resource_id=str(sale.id),
            status="success",
        ),
        AuditEvent(
            actor_user=actor,
            category="BUSINESS",
            action="recovery.create",
            resource_type="Recovery",
            resource_id=str(recovery.id),
            status="success",
        ),
    ])

    grant(actor, "customer.timeline")
    client = APIClient()
    client.force_authenticate(user=actor)
    response = client.get(f"/api/v1/crm/customers/{customer.pk}/timeline/")

    assert response.status_code == 200
    actions = {item["action"] for item in response.data["results"]}
    assert {
        "customer.lifecycle_changed",
        "portfolio.transfer",
        "creditsale.status_change",
        "recovery.create",
    } <= actions


@pytest.mark.django_db
def test_timeline_is_scoped_to_customer_portfolio():
    owner = User.objects.create_user(
        username="v6-timeline-owner",
        email="v6-timeline-owner@example.com",
        password="x",
        is_active=True,
    )
    other = User.objects.create_user(
        username="v6-timeline-other",
        email="v6-timeline-other@example.com",
        password="x",
        is_active=True,
    )
    portfolio = Portfolio.objects.create(
        ref="PF-V6-TIMELINE-SCOPE",
        commercial=owner,
        active=True,
    )
    customer = Customer.objects.create(
        email="scoped@example.com",
        phone="+24106000004",
        portfolio=portfolio,
    )
    grant(other, "customer.timeline")

    client = APIClient()
    client.force_authenticate(user=other)
    response = client.get(f"/api/v1/crm/customers/{customer.pk}/timeline/")

    assert response.status_code in (403, 404)
