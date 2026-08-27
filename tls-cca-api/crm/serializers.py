""" CRM Serializers """

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, PhysicalPersonDetail, MoralPersonDetail, Portfolio, PortfolioTransfer
from crm.services import customer_services as services
from core.mixins.serializers import HistoricalChangesMixin

User = get_user_model()

class PortfolioSerializer(serializers.ModelSerializer):
    """
    Serializer for the Portfolio model.
    """
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'ref', 'commercial', 'commercial_name', 'description', 
            'balance', 'active', 'created_at', 'last_transfer_date'
        ]
        read_only_fields = ('ref', 'active', 'balance', 'created_at', 'commercial_name', 'last_transfer_date')


class CustomerDeactivationPolicySerializer(serializers.Serializer):
    """
    Serializer for the customer inactivity auto-deactivation policy.
    Only Administrators can read/update it.
    - `inactivity_months`: the exact inactivity duration (in months) after which
      an inactive customer is deactivated. Default: 48 (4 years).
    """
    inactivity_months = serializers.IntegerField(
        min_value=1, max_value=600,
        help_text="Inactivity duration in months after which a customer is deactivated.",
    )


class PortfolioAssignSerializer(serializers.Serializer):
    """
    Input serializer for the portfolio `assign` action.
    Accepts an active target commercial and an optional reason.
    """
    commercial = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        help_text='Target commercial (must be active) receiving the portfolio',
    )
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PortfolioTransferInputSerializer(serializers.Serializer):
    """
    Input serializer for the portfolio `transfer` action.
    Accepts an active target commercial and an optional reason.
    """
    to_commercial = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        help_text='Target commercial (must be active) receiving the portfolio',
    )
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PortfolioTransferSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the PortfolioTransfer journal (assignment/transfer audit).
    """
    portfolio_ref = serializers.CharField(source='portfolio.ref', read_only=True)
    from_commercial_name = serializers.CharField(source='from_commercial.get_full_name', read_only=True)
    to_commercial_name = serializers.CharField(source='to_commercial.get_full_name', read_only=True)
    transferred_by_name = serializers.CharField(source='transferred_by.get_full_name', read_only=True)

    class Meta:
        model = PortfolioTransfer
        fields = [
            'id', 'portfolio', 'portfolio_ref',
            'from_commercial', 'from_commercial_name',
            'to_commercial', 'to_commercial_name',
            'transferred_by', 'transferred_by_name',
            'reason', 'transferred_at',
        ]
        read_only_fields = fields


class PhysicalPersonDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for physical person details.
    Intended to be used nested within the CustomerSerializer.
    """
    class Meta:
        model = PhysicalPersonDetail
        exclude = ['customer']


class MoralPersonDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for moral person details.
    Intended to be used nested within the CustomerSerializer.
    """
    class Meta:
        model = MoralPersonDetail
        exclude = ['customer']


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Customer model.
    Handles nested creation and update of PhysicalPersonDetail or MoralPersonDetail
    based on the 'customer_type'.
    """
    physical_detail = PhysicalPersonDetailSerializer(required=False, allow_null=True)
    moral_detail = MoralPersonDetailSerializer(required=False, allow_null=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'display_name', 'customer_type', 'portfolio', 'email', 'phone', 
            'mobile', 'address', 'is_active', 'created_at', 'physical_detail', 'moral_detail'
        ]
        read_only_fields = ('created_at', 'portfolio', 'display_name')

    def validate(self, data):
        customer_type = data.get('customer_type')
        physical_detail_data = data.get('physical_detail')
        moral_detail_data = data.get('moral_detail')

        if customer_type == Customer.TYPE_PHYSICAL and not physical_detail_data:
            raise serializers.ValidationError("Physical details are required for a physical person.")
        if customer_type == Customer.TYPE_MORAL and not moral_detail_data:
            raise serializers.ValidationError("Moral details are required for a moral person.")
        
        if customer_type == Customer.TYPE_PHYSICAL and moral_detail_data:
            data.pop('moral_detail', None)
        if customer_type == Customer.TYPE_MORAL and physical_detail_data:
            data.pop('physical_detail', None)

        return data

    def create(self, validated_data):
        # Delegate creation to the customer service
        return services.create_customer(validated_data)

    def update(self, instance, validated_data):
        # Delegate update to the customer service
        return services.update_customer(instance, validated_data)

class HistoricalCustomerSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    """
    Serializer for the Customer model.
    """
    class Meta:
        model = Customer.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 'history_user', 'changes',
            'customer_type', 'portfolio', 'email', 'phone', 'is_active'
        ]

class HistoricalPortfolioSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    """
    Serializer for the PortfolioHistory model.
    """
    commercial_type_display = serializers.CharField(source='commercial.get_full_name', read_only=True)

    class Meta:
        model = Portfolio.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 'history_user', 'changes',
            'ref', 'commercial_type_display', 'description', 'balance', 'active'
        ]