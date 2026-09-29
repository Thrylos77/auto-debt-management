"""Tests for the enriched Customer 360 profile."""

from datetime import date

import pytest
from django.db import IntegrityError

from crm.models import Customer, CustomerAddress, MoralPersonDetail, PhysicalPersonDetail
from crm.serializers import (
    CustomerAddressSerializer,
    CustomerSerializer,
    MoralPersonDetailSerializer,
    PhysicalPersonDetailSerializer,
)


@pytest.mark.django_db
def test_customer_accepts_multiple_structured_addresses_and_contact_details():
    customer = Customer.objects.create(
        phone="24106000000",
        email="client@example.com",
        secondary_email="billing@example.com",
        mobile="24107000000",
        preferred_contact_channel=Customer.CONTACT_EMAIL,
        address="Former free-text address",
    )

    primary = CustomerAddress.objects.create(
        customer=customer,
        address_type=CustomerAddress.ADDRESS_RESIDENTIAL,
        label="Domicile",
        address_line_1="12 Rue du Commerce",
        address_line_2="Immeuble Horizon, 3e étage",
        neighborhood="Louis",
        city="Libreville",
        state_region="Estuaire",
        postal_code="BP 100",
        country="Gabon",
        country_code="GA",
        is_primary=True,
    )
    billing = CustomerAddress.objects.create(
        customer=customer,
        address_type=CustomerAddress.ADDRESS_BILLING,
        address_line_1="25 Boulevard de l'Indépendance",
        neighborhood="Centre-ville",
        city="Libreville",
        country="Gabon",
        country_code="GA",
    )

    primary.full_clean()
    primary.save()

    assert customer.addresses.count() == 2
    assert customer.addresses.get(pk=primary.pk).country_code == "GA"
    assert billing.address_type == CustomerAddress.ADDRESS_BILLING
    assert customer.preferred_contact_channel == Customer.CONTACT_EMAIL


@pytest.mark.django_db
def test_customer_has_only_one_primary_address_at_database_level():
    customer = Customer.objects.create(phone="24106000006")
    CustomerAddress.objects.create(
        customer=customer,
        address_type=CustomerAddress.ADDRESS_RESIDENTIAL,
        city="Libreville",
        country="Gabon",
        country_code="GA",
        is_primary=True,
    )

    with pytest.raises(IntegrityError):
        CustomerAddress.objects.create(
            customer=customer,
            address_type=CustomerAddress.ADDRESS_BILLING,
            city="Libreville",
            country="Gabon",
            country_code="GA",
            is_primary=True,
        )


@pytest.mark.django_db
def test_customer_serializer_returns_structured_addresses():
    customer = Customer.objects.create(phone="24106000001")
    CustomerAddress.objects.create(
        customer=customer,
        address_type=CustomerAddress.ADDRESS_LEGAL,
        address_line_1="10 Avenue des Travaux",
        neighborhood="Akanda",
        city="Libreville",
        country="Gabon",
        country_code="GA",
        is_primary=True,
    )

    data = CustomerSerializer(customer).data

    assert data["addresses"][0]["neighborhood"] == "Akanda"
    assert data["addresses"][0]["city"] == "Libreville"
    assert data["addresses"][0]["country"] == "Gabon"
    assert data["addresses"][0]["country_code"] == "GA"


@pytest.mark.django_db
def test_physical_person_profile_contains_professional_identity_fields():
    customer = Customer.objects.create(phone="24106000002")
    detail = PhysicalPersonDetail.objects.create(
        customer=customer,
        first_name="Jean",
        middle_names="Pierre",
        last_name="Moubamba",
        preferred_name="Jean-Pierre",
        birth_day=date(1990, 4, 5),
        birth_place="Libreville",
        birth_city="Libreville",
        birth_country="Gabon",
        nationality="Gabonese",
        id_document_type="passport",
        id_document_number="P123456",
        id_document_issuing_authority="DGDI",
        id_document_issuer_country="Gabon",
        id_document_issued_at=date(2025, 1, 10),
        id_document_expires_at=date(2030, 1, 10),
        occupation="Accountant",
        employer_name="Example SA",
    )

    data = PhysicalPersonDetailSerializer(detail).data

    assert data["middle_names"] == "Pierre"
    assert data["birth_city"] == "Libreville"
    assert data["id_document_issuing_authority"] == "DGDI"
    assert data["occupation"] == "Accountant"


@pytest.mark.django_db
def test_moral_person_profile_contains_legal_business_and_representative_details():
    customer = Customer.objects.create(
        customer_type=Customer.TYPE_MORAL,
        phone="24106000003",
    )
    detail = MoralPersonDetail.objects.create(
        customer=customer,
        business_name="Example Gabon SA",
        trading_name="Example",
        registration_number="RC-LBV-001",
        tax_identification_number="NIF-001",
        legal_form="SA",
        incorporation_date=date(2020, 3, 15),
        registration_country="Gabon",
        activity_sector="Services financiers",
        primary_activity="Conseil et accompagnement des entreprises.",
        website="https://example.com",
        representative_first_name="Marie",
        representative_last_name="Ndong",
        representative_function="Directrice générale",
        representative_id_document_type="national_id",
        representative_id_document="ID-123456",
        representative_id_issuer_country="Gabon",
        representative_id_issued_at=date(2024, 6, 1),
        representative_id_expires_at=date(2029, 6, 1),
        representative_email="representative@example.com",
        representative_phone="24106000004",
    )

    data = MoralPersonDetailSerializer(detail).data

    assert data["trading_name"] == "Example"
    assert data["tax_identification_number"] == "NIF-001"
    assert data["activity_sector"] == "Services financiers"
    assert data["representative_function"] == "Directrice générale"


def test_customer_serializer_exposes_professional_profile_and_protects_internal_fields():
    serializer = CustomerSerializer()

    assert serializer.fields["addresses"].read_only is False
    assert serializer.fields["secondary_email"].read_only is False
    assert serializer.fields["preferred_contact_channel"].read_only is False
    assert serializer.fields["lifecycle_status"].read_only is True
    assert serializer.fields["portfolio"].read_only is True


@pytest.mark.django_db
def test_customer_serializer_creates_and_updates_structured_addresses():
    serializer = CustomerSerializer(data={
        "customer_type": Customer.TYPE_PHYSICAL,
        "email": "nested@example.com",
        "phone": "24106000005",
        "physical_detail": {
            "first_name": "Anne",
            "last_name": "Mba",
        },
        "addresses": [
            {
                "address_type": "residential",
                "address_line_1": "12 Rue de la Paix",
                "neighborhood": "Glass",
                "city": "Libreville",
                "country": "Gabon",
                "country_code": "ga",
                "is_primary": True,
            },
        ],
    })
    assert serializer.is_valid(), serializer.errors
    customer = serializer.save()

    address = customer.addresses.get()
    assert address.is_primary is True
    assert address.country_code == "GA"

    update_serializer = CustomerSerializer(
        customer,
        data={
            "addresses": [
                {
                    "id": address.id,
                    "address_type": "billing",
                    "address_line_1": "25 Boulevard de l'Indépendance",
                    "neighborhood": "Centre-ville",
                    "city": "Libreville",
                    "country": "Gabon",
                    "country_code": "GA",
                    "is_primary": True,
                },
            ],
        },
        partial=True,
    )
    assert update_serializer.is_valid(), update_serializer.errors
    update_serializer.save()

    address.refresh_from_db()
    assert address.address_type == "billing"
    assert address.address_line_1 == "25 Boulevard de l'Indépendance"
    assert customer.addresses.filter(is_primary=True).count() == 1


def test_customer_address_serializer_normalizes_lowercase_country_code():
    serializer = CustomerAddressSerializer(
        data={
            "address_type": "residential",
            "city": "Libreville",
            "country": "Gabon",
            "country_code": "ga",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["country_code"] == "GA"


def test_customer_address_serializer_exposes_location_components():
    serializer = CustomerAddressSerializer()

    for field_name in (
        "address_line_1",
        "neighborhood",
        "city",
        "state_region",
        "postal_code",
        "country",
        "country_code",
    ):
        assert serializer.fields[field_name].read_only is False


def test_person_document_dates_are_validated():
    serializer = PhysicalPersonDetailSerializer(
        data={
            "id_document_issued_at": "2026-01-01",
            "id_document_expires_at": "2025-01-01",
        }
    )
    assert serializer.is_valid() is False
    assert "expiry date" in str(serializer.errors).lower()


def test_representative_document_dates_are_validated():
    serializer = MoralPersonDetailSerializer(
        data={
            "representative_id_issued_at": "2026-01-01",
            "representative_id_expires_at": "2025-01-01",
        }
    )
    assert serializer.is_valid() is False
    assert "expiry date" in str(serializer.errors).lower()
