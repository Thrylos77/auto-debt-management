"""Customer duplicate detection tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from audit.models import AuditEvent
from crm.models import Customer, MoralPersonDetail, PhysicalPersonDetail
from crm.services.customer_duplicate_service import find_duplicate_candidates
from rbac.models import Permission, Role, RoleAssignment

User = get_user_model()


def grant(user, *codes):
    role, _ = Role.objects.get_or_create(name=f"V6_DUP_{user.pk}")
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, label=code)
        role.permissions.add(permission)
    RoleAssignment.objects.get_or_create(user=user, role=role)


@pytest.mark.django_db
def test_duplicate_check_finds_exact_email_phone_and_identifier():
    customer = Customer.objects.create(
        email="existing@example.com",
        phone="+24106000000",
    )
    PhysicalPersonDetail.objects.create(
        customer=customer,
        id_document_number="AB-123-XY",
        first_name="Existing",
        last_name="Customer",
    )

    candidates = find_duplicate_candidates(
        email=" EXISTING@example.com ",
        phone="00 241 06 00 00 00",
        id_document_number="ab123xy",
    )

    assert len(candidates) == 1
    assert candidates[0]["customer_id"] == customer.id
    assert candidates[0]["confidence"] == 1.0
    assert "email" in candidates[0]["matched_fields"]
    assert "phone" in candidates[0]["matched_fields"]
    assert "id_document_number" in candidates[0]["matched_fields"]


@pytest.mark.django_db
def test_duplicate_check_tolerates_lower_confidence_candidate_without_deleting():
    customer = Customer.objects.create(
        email="other@example.com",
        phone="+24106000001",
    )
    before = Customer.objects.count()

    candidates = find_duplicate_candidates(phone="00 241 06 00 00 01")

    assert candidates[0]["customer_id"] == customer.id
    assert candidates[0]["confidence"] == 0.9
    assert Customer.objects.count() == before


@pytest.mark.django_db
def test_duplicate_endpoint_requires_permission_and_audits_check():
    actor = User.objects.create_user(
        username="v6-duplicate-actor",
        email="v6-duplicate-actor@example.com",
        password="x",
        is_active=True,
    )
    existing = Customer.objects.create(
        email="existing-check@example.com",
        phone="+24106000002",
    )
    client = APIClient()
    client.force_authenticate(user=actor)

    denied = client.post(
        "/api/v1/crm/customers/duplicates/check/",
        {"email": existing.email},
        format="json",
    )
    assert denied.status_code == 403

    grant(actor, "customer.duplicate_check")
    allowed = client.post(
        "/api/v1/crm/customers/duplicates/check/",
        {"email": "existing-check@example.com"},
        format="json",
    )
    assert allowed.status_code == 200
    assert allowed.data["candidates"][0]["customer_id"] == existing.id

    assert AuditEvent.objects.filter(
        action="customer.duplicate_check",
        actor_user=actor,
    ).exists()
    assert AuditEvent.objects.filter(
        action="customer.duplicate_detected",
        actor_user=actor,
    ).exists()


@pytest.mark.django_db
def test_tax_identification_number_is_a_strong_moral_duplicate_signal():
    customer = Customer.objects.create(
        customer_type=Customer.TYPE_MORAL,
        phone="24106000050",
    )
    MoralPersonDetail.objects.create(
        customer=customer,
        business_name="Tax Identity SA",
        tax_identification_number="NIF-STRONG-001",
    )

    candidates = find_duplicate_candidates(
        tax_identification_number="nif strong 001",
    )

    assert candidates[0]["customer_id"] == customer.id
    assert candidates[0]["confidence"] == 1.0
    assert "tax_identification_number" in candidates[0]["matched_fields"]
