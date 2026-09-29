"""Serializer-level mass-assignment protections for CRM resources."""

from crm.serializers import (
    CustomerDuplicateCheckResponseSerializer,
    HistoricalCustomerSerializer,
    CustomerDuplicateCheckSerializer,
    CustomerLifecycleSerializer,
    CustomerSerializer,
    CustomerTimelineItemSerializer,
    PortfolioSerializer,
)


def test_customer_is_active_is_read_only():
    serializer = CustomerSerializer()

    assert serializer.fields["is_active"].read_only is True


def test_portfolio_commercial_is_read_only():
    serializer = PortfolioSerializer()

    assert serializer.fields["commercial"].read_only is True


def test_customer_lifecycle_internal_fields_are_read_only():
    serializer = CustomerSerializer()

    for field_name in (
        "is_active",
        "lifecycle_status",
        "status_changed_at",
        "status_changed_by_id",
        "status_reason",
        "portfolio",
    ):
        assert serializer.fields[field_name].read_only is True


def test_lifecycle_serializer_does_not_accept_status():
    serializer = CustomerLifecycleSerializer(data={"lifecycle_status": "blocked"})

    assert serializer.is_valid()
    assert "lifecycle_status" not in serializer.validated_data


def test_historical_customer_serializer_matches_customer_history_model():
    serializer = HistoricalCustomerSerializer()

    assert "address" in serializer.fields
    for field_name in (
        "address_line_1",
        "neighborhood",
        "city",
        "country",
        "country_code",
    ):
        assert field_name not in serializer.fields


def test_timeline_and_duplicate_candidate_contracts_are_serializers():
    assert CustomerTimelineItemSerializer().fields["metadata"].read_only is True
    assert CustomerDuplicateCheckSerializer().fields["email"].write_only is False
    response = CustomerDuplicateCheckResponseSerializer(
        data={"candidates": []},
    )
    assert response.is_valid()
