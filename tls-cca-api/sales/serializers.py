# sales/serializers.py
from rest_framework import serializers

from core.serializers.mixins import HistoricalChangesMixin
from .models import CreditSale


class CreditSaleSerializer(serializers.ModelSerializer):
    """
    Serializer for the CreditSale model.
    """
    customer_display_name = serializers.CharField(source='customer.display_name', read_only=True)
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True)
    portfolio_name = serializers.CharField(source='portfolio.name', read_only=True)

    class Meta:
        model = CreditSale
        fields = [
            'id', 
            'customer', 'customer_display_name',
            'commercial', 'commercial_name',
            'portfolio', 'portfolio_name',
            'sale_date', 
            'total_amount', 
            'deposit', 
            'status', 
            'proof_doc'
        ]
        read_only_fields = ('sale_date', 'status')

    def create(self, validated_data):
        # Automatically set the commercial to the user making the request
        validated_data['commercial'] = self.context['request'].user
        return super().create(validated_data)

class HistoricalCreditSaleSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    """
    Serializer for the CreditSale history model.
    """
    customer_display_name = serializers.CharField(source='customer.display_name', read_only=True)
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True)
    portfolio_ref = serializers.CharField(source='portfolio.ref', read_only=True)

    class Meta:
        model = CreditSale.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 'history_user', 'changes',
            'customer_display_name', 'commercial', 'commercial_name',
            'portfolio_ref', 'sale_date', 'total_amount', 
            'deposit', 'status', 'proof_doc'
        ]