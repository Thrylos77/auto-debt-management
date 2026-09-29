"""Non-destructive customer duplicate detection."""

import re

from crm.models import Customer, MoralPersonDetail, PhysicalPersonDetail


_NON_ALNUM = re.compile(r"[^A-Z0-9]+")
_DIGITS = re.compile(r"\D+")


def normalize_email(value):
    """Normalize an email for duplicate comparison without changing stored data."""
    return str(value or "").strip().casefold()


def normalize_phone(value):
    """Normalize a phone number to digits while preserving a simple country prefix."""
    digits = _DIGITS.sub("", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def normalize_identity(value):
    """Normalize identity/registration identifiers for comparison."""
    return _NON_ALNUM.sub("", str(value or "").strip().upper())


def find_duplicate_candidates(
    *,
    email=None,
    phone=None,
    mobile=None,
    id_document_number=None,
    registration_number=None,
    tax_identification_number=None,
    exclude_customer_id=None,
):
    """Return ranked duplicate candidates without creating, merging or deleting data."""
    normalized_email = normalize_email(email)
    normalized_phones = {
        normalized
        for normalized in (
            normalize_phone(phone),
            normalize_phone(mobile),
        )
        if normalized
    }
    normalized_identity = normalize_identity(id_document_number)
    normalized_registration = normalize_identity(registration_number)
    normalized_tax_id = normalize_identity(tax_identification_number)

    customers = Customer.objects.all().prefetch_related(
        "physical_detail",
        "moral_detail",
    )
    if exclude_customer_id is not None:
        customers = customers.exclude(pk=exclude_customer_id)

    candidates = []
    for customer in customers:
        matched_fields = []
        reasons = []
        score = 0.0

        customer_email = normalize_email(customer.email)
        customer_phones = {
            normalized
            for normalized in (
                normalize_phone(customer.phone),
                normalize_phone(customer.mobile),
            )
            if normalized
        }

        if normalized_identity:
            try:
                stored_identity = normalize_identity(
                    customer.physical_detail.id_document_number
                )
            except PhysicalPersonDetail.DoesNotExist:
                stored_identity = ""
            if stored_identity and stored_identity == normalized_identity:
                matched_fields.append("id_document_number")
                reasons.append("same identity document number")
                score = max(score, 1.0)

        if normalized_registration or normalized_tax_id:
            try:
                stored_registration = normalize_identity(
                    customer.moral_detail.registration_number
                )
                stored_tax_id = normalize_identity(
                    customer.moral_detail.tax_identification_number
                )
            except MoralPersonDetail.DoesNotExist:
                stored_registration = ""
                stored_tax_id = ""

            if normalized_registration and stored_registration == normalized_registration:
                matched_fields.append("registration_number")
                reasons.append("same company registration number")
                score = max(score, 1.0)

            if normalized_tax_id and stored_tax_id == normalized_tax_id:
                matched_fields.append("tax_identification_number")
                reasons.append("same tax identification number")
                score = max(score, 1.0)

        if normalized_email and customer_email == normalized_email:
            matched_fields.append("email")
            reasons.append("same normalized email")
            score = max(score, 0.92)

        if normalized_phones and customer_phones.intersection(normalized_phones):
            matched_fields.append("phone")
            reasons.append("same normalized phone")
            score = max(score, 0.90)

        if len(matched_fields) >= 2 and "email" in matched_fields and "phone" in matched_fields:
            score = max(score, 0.98)

        if not matched_fields:
            continue

        candidates.append({
            "customer_id": customer.pk,
            "display_name": customer.display_name,
            "customer_type": customer.customer_type,
            "confidence": round(score, 2),
            "matched_fields": matched_fields,
            "reasons": reasons,
        })

    candidates.sort(
        key=lambda item: (-item["confidence"], item["customer_id"]),
    )
    return candidates
