"""CRM API serializers."""

from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework import serializers

from core.mixins.serializers import HistoricalChangesMixin
from crm.models import (
    Customer,
    CustomerAddress,
    MoralPersonDetail,
    PhysicalPersonDetail,
    Portfolio,
    PortfolioTransfer,
)
from crm.services import customer_services as services

User = get_user_model()


class PortfolioSerializer(serializers.ModelSerializer):
    """Read/write representation of a portfolio, with owner controlled by services."""

    commercial_name = serializers.CharField(
        source="commercial.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "ref",
            "commercial",
            "commercial_name",
            "description",
            "balance",
            "active",
            "created_at",
            "last_transfer_date",
        ]
        read_only_fields = (
            "ref",
            "commercial",
            "active",
            "balance",
            "created_at",
            "commercial_name",
            "last_transfer_date",
        )


class CustomerDeactivationPolicySerializer(serializers.Serializer):
    """Serializer for the configurable customer inactivity policy."""

    inactivity_months = serializers.IntegerField(
        min_value=1,
        max_value=600,
        help_text="Inactivity duration in months after which a customer is deactivated.",
    )


class CustomerBulkDeactivationResponseSerializer(serializers.Serializer):
    """Response returned by the automatic customer deactivation endpoint."""

    checked_customers = serializers.IntegerField()
    deactivated_customers = serializers.IntegerField()
    detail = serializers.CharField()


class CustomerLifecycleSerializer(serializers.Serializer):
    """Input for an explicit lifecycle transition."""

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )


class CustomerDuplicateCheckSerializer(serializers.Serializer):
    """Identity data used only for non-destructive duplicate detection."""

    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    mobile = serializers.CharField(required=False, allow_blank=True, max_length=30)
    id_document_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    registration_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    tax_identification_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )

    def validate(self, attrs):
        if not any(value.strip() if isinstance(value, str) else value for value in attrs.values()):
            raise serializers.ValidationError(
                "At least one duplicate identity field is required."
            )
        return attrs


class CustomerDuplicateCandidateSerializer(serializers.Serializer):
    """Ranked non-destructive duplicate candidate."""

    customer_id = serializers.IntegerField()
    display_name = serializers.CharField()
    customer_type = serializers.CharField()
    confidence = serializers.FloatField(min_value=0, max_value=1)
    matched_fields = serializers.ListField(child=serializers.CharField())
    reasons = serializers.ListField(child=serializers.CharField())


class CustomerDuplicateCheckResponseSerializer(serializers.Serializer):
    """Envelope returned by the duplicate-check endpoint."""

    candidates = CustomerDuplicateCandidateSerializer(many=True)


class CustomerTimelineItemSerializer(serializers.Serializer):
    """Public representation of one customer timeline item."""

    id = serializers.IntegerField()
    occurred_at = serializers.DateTimeField()
    action = serializers.CharField()
    status = serializers.CharField()
    reason = serializers.CharField(allow_blank=True)
    actor_id = serializers.IntegerField(allow_null=True)
    actor_name = serializers.CharField()
    metadata = serializers.JSONField(read_only=True)
    resource_type = serializers.CharField()
    resource_id = serializers.CharField(allow_blank=True)


class PortfolioAssignSerializer(serializers.Serializer):
    """Input serializer for a portfolio assignment."""

    commercial = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        help_text="Target active commercial receiving the portfolio.",
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PortfolioTransferInputSerializer(serializers.Serializer):
    """Input serializer for a portfolio transfer."""

    to_commercial = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        help_text="Target active commercial receiving the portfolio.",
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PortfolioTransferSerializer(serializers.ModelSerializer):
    """Read-only representation of the immutable portfolio transfer journal."""

    portfolio_ref = serializers.CharField(source="portfolio.ref", read_only=True)
    from_commercial_name = serializers.CharField(
        source="from_commercial.get_full_name",
        read_only=True,
    )
    to_commercial_name = serializers.CharField(
        source="to_commercial.get_full_name",
        read_only=True,
    )
    transferred_by_name = serializers.CharField(
        source="transferred_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = PortfolioTransfer
        fields = [
            "id",
            "portfolio",
            "portfolio_ref",
            "from_commercial",
            "from_commercial_name",
            "to_commercial",
            "to_commercial_name",
            "transferred_by",
            "transferred_by_name",
            "reason",
            "transferred_at",
        ]
        read_only_fields = fields


class CustomerAddressSerializer(serializers.ModelSerializer):
    """Nested structured customer address representation."""

    id = serializers.IntegerField(required=False)
    country_code = serializers.CharField(
        max_length=2,
        required=False,
        allow_blank=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z]{2}$",
                message="Country code must use the ISO 3166-1 alpha-2 format.",
            )
        ],
    )

    class Meta:
        model = CustomerAddress
        exclude = ["customer"]
        read_only_fields = ("created_at", "updated_at")

    def validate(self, attrs):
        country_code = attrs.get("country_code")
        if country_code:
            attrs["country_code"] = country_code.upper()
        return attrs


class PhysicalPersonDetailSerializer(serializers.ModelSerializer):
    """Nested professional physical-person profile."""

    class Meta:
        model = PhysicalPersonDetail
        exclude = ["customer"]

    def validate(self, attrs):
        issued_at = attrs.get("id_document_issued_at")
        expires_at = attrs.get("id_document_expires_at")

        if issued_at and expires_at and expires_at < issued_at:
            raise serializers.ValidationError(
                "Identity document expiry date cannot precede its issue date."
            )
        return attrs


class MoralPersonDetailSerializer(serializers.ModelSerializer):
    """Nested professional legal and operational company profile."""

    class Meta:
        model = MoralPersonDetail
        exclude = ["customer"]

    def validate(self, attrs):
        issued_at = attrs.get("representative_id_issued_at")
        expires_at = attrs.get("representative_id_expires_at")

        if issued_at and expires_at and expires_at < issued_at:
            raise serializers.ValidationError(
                "Representative document expiry date cannot precede its issue date."
            )
        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    """Professional Customer 360 representation."""

    addresses = CustomerAddressSerializer(many=True, required=False)
    physical_detail = PhysicalPersonDetailSerializer(
        required=False,
        allow_null=True,
    )
    moral_detail = MoralPersonDetailSerializer(
        required=False,
        allow_null=True,
    )
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "display_name",
            "customer_type",
            "portfolio",
            "email",
            "secondary_email",
            "phone",
            "mobile",
            "preferred_contact_channel",
            "address",
            "addresses",
            "is_active",
            "lifecycle_status",
            "status_changed_at",
            "status_changed_by_id",
            "status_reason",
            "created_at",
            "physical_detail",
            "moral_detail",
        ]
        read_only_fields = (
            "id",
            "created_at",
            "portfolio",
            "is_active",
            "lifecycle_status",
            "status_changed_at",
            "status_changed_by_id",
            "status_reason",
            "display_name",
        )

    def validate(self, data):
        customer_type = data.get(
            "customer_type",
            getattr(self.instance, "customer_type", None),
        )
        physical_detail_data = data.get("physical_detail")
        moral_detail_data = data.get("moral_detail")
        addresses = data.get("addresses", [])

        if customer_type == Customer.TYPE_PHYSICAL and moral_detail_data:
            raise serializers.ValidationError(
                "A physical customer cannot accept moral person details."
            )
        if customer_type == Customer.TYPE_MORAL and physical_detail_data:
            raise serializers.ValidationError(
                "A moral customer cannot accept physical person details."
            )

        if self.instance is None:
            if customer_type == Customer.TYPE_PHYSICAL and not physical_detail_data:
                raise serializers.ValidationError(
                    "Physical details are required for a physical person."
                )
            if customer_type == Customer.TYPE_MORAL and not moral_detail_data:
                raise serializers.ValidationError(
                    "Moral details are required for a moral person."
                )

        primary_addresses = [
            address for address in addresses if address.get("is_primary")
        ]
        if len(primary_addresses) > 1:
            raise serializers.ValidationError(
                "Only one primary address may be supplied in a request."
            )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        return services.create_customer(
            validated_data,
            creator=request.user if request else None,
            request=request,
        )

    def update(self, instance, validated_data):
        request = self.context.get("request")
        return services.update_customer(
            instance,
            validated_data,
            actor=request.user if request else None,
            request=request,
        )


class HistoricalCustomerSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    """Historical representation of Customer."""

    class Meta:
        model = Customer.history.model
        fields = [
            "history_id",
            "history_date",
            "history_type_display",
            "history_user",
            "changes",
            "customer_type",
            "portfolio",
            "email",
            "secondary_email",
            "phone",
            "mobile",
            "preferred_contact_channel",
            "address",
            "is_active",
            "lifecycle_status",
            "status_changed_at",
            "status_changed_by_id",
            "status_reason",
        ]


class HistoricalPortfolioSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    """Historical representation of Portfolio."""

    commercial_type_display = serializers.CharField(
        source="commercial.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Portfolio.history.model
        fields = [
            "history_id",
            "history_date",
            "history_type_display",
            "history_user",
            "changes",
            "ref",
            "commercial_type_display",
            "description",
            "balance",
            "active",
        ]
