"""CRM lifecycle transition tests."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from audit.models import AuditEvent
from crm.models import Customer, Portfolio
from crm.services.customer_services import (
    activate_customer,
    archive_customer,
    block_customer,
    deactivate_customer,
    suspend_customer,
    unblock_customer,
)
from rbac.models import Permission, Role, RoleAssignment

User = get_user_model()


def grant(user, code):
    role, _ = Role.objects.get_or_create(
        name=f"V6_{code.replace('.', '_')}_{user.pk}"
    )
    permission, _ = Permission.objects.get_or_create(code=code, label=code)
    role.permissions.add(permission)
    RoleAssignment.objects.get_or_create(user=user, role=role)


def customer_for(user, lifecycle_status=Customer.LIFECYCLE_ACTIVE):
    portfolio = Portfolio.objects.create(
        ref=f"PF-V6-{user.pk}-{Customer.objects.count()}",
        commercial=user,
        active=True,
    )
    return Customer.objects.create(
        phone=f"12345{Customer.objects.count():05d}",
        portfolio=portfolio,
        lifecycle_status=lifecycle_status,
        is_active=lifecycle_status in {
            Customer.LIFECYCLE_PROSPECT,
            Customer.LIFECYCLE_ACTIVE,
        },
    )


@pytest.mark.django_db
def test_every_documented_lifecycle_transition_is_valid():
    actor = User.objects.create_user(
        username="v6-lifecycle-actor",
        email="v6-lifecycle-actor@example.com",
        password="x",
        is_active=True,
    )
    actor.is_superuser = True
    actor.save(update_fields=["is_superuser"])

    prospect = customer_for(actor, Customer.LIFECYCLE_PROSPECT)
    activate_customer(prospect, actor=actor, reason="qualification")
    assert prospect.refresh_from_db() is None
    assert prospect.lifecycle_status == Customer.LIFECYCLE_ACTIVE

    active = customer_for(actor)
    suspend_customer(active, actor=actor, reason="review")
    active.refresh_from_db()
    assert active.lifecycle_status == Customer.LIFECYCLE_SUSPENDED

    block_customer(active, actor=actor, reason="compliance")
    active.refresh_from_db()
    assert active.lifecycle_status == Customer.LIFECYCLE_BLOCKED

    unblock_customer(active, actor=actor, reason="resolved")
    active.refresh_from_db()
    assert active.lifecycle_status == Customer.LIFECYCLE_ACTIVE

    deactivate_customer(active, actor=actor, reason="inactivity")
    active.refresh_from_db()
    assert active.lifecycle_status == Customer.LIFECYCLE_INACTIVE

    archive_customer(active, actor=actor, reason="closed")
    active.refresh_from_db()
    assert active.lifecycle_status == Customer.LIFECYCLE_ARCHIVED
    assert active.is_active is False


@pytest.mark.django_db
def test_forbidden_lifecycle_transition_is_rejected():
    actor = User.objects.create_user(
        username="v6-lifecycle-invalid",
        email="v6-lifecycle-invalid@example.com",
        password="x",
        is_active=True,
    )
    actor.is_superuser = True
    actor.save(update_fields=["is_superuser"])
    customer = customer_for(actor, Customer.LIFECYCLE_ARCHIVED)

    with pytest.raises(ValidationError):
        activate_customer(customer, actor=actor)


@pytest.mark.django_db
def test_lifecycle_requires_permission_and_scope():
    actor = User.objects.create_user(
        username="v6-lifecycle-permission",
        email="v6-lifecycle-permission@example.com",
        password="x",
        is_active=True,
    )
    owner = User.objects.create_user(
        username="v6-lifecycle-owner",
        email="v6-lifecycle-owner@example.com",
        password="x",
        is_active=True,
    )
    customer = customer_for(owner)
    grant(actor, "customer.suspend")

    with pytest.raises(PermissionDenied):
        suspend_customer(customer, actor=actor)


@pytest.mark.django_db
def test_lifecycle_writes_audit_and_synchronizes_legacy_flag():
    actor = User.objects.create_superuser(
        username="v6-lifecycle-audit",
        email="v6-lifecycle-audit@example.com",
        password="x",
    )
    customer = customer_for(actor)

    deactivate_customer(
        customer,
        actor=actor,
        reason="account closed",
    )
    customer.refresh_from_db()

    assert customer.is_active is False
    assert customer.lifecycle_status == Customer.LIFECYCLE_INACTIVE
    assert customer.status_changed_by_id == actor.id
    assert customer.status_reason == "account closed"

    event = AuditEvent.objects.get(
        action="customer.lifecycle_changed",
        resource_type="Customer",
        resource_id=str(customer.id),
    )
    assert event.metadata == {
        "previous_status": Customer.LIFECYCLE_ACTIVE,
        "new_status": Customer.LIFECYCLE_INACTIVE,
    }


@pytest.mark.django_db
def test_patch_cannot_change_lifecycle_directly():
    actor = User.objects.create_superuser(
        username="v6-lifecycle-patch",
        email="v6-lifecycle-patch@example.com",
        password="x",
    )
    customer = customer_for(actor)
    api_client = APIClient()
    api_client.force_authenticate(user=actor)

    response = api_client.patch(
        f"/api/v1/crm/customers/{customer.pk}/",
        {"lifecycle_status": Customer.LIFECYCLE_BLOCKED},
        format="json",
    )

    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.lifecycle_status == Customer.LIFECYCLE_ACTIVE
