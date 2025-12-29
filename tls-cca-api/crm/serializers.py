# crm/serializers.py
from rest_framework import serializers
from .models import Customer, PhysicalPersonDetail, MoralPersonDetail, Portfolio
from crm.services import customer_services as services
from core.mixins.serializers import HistoricalChangesMixin

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