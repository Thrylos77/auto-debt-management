# receivables/serializers.py
from rest_framework import serializers

from core.serializers.mixins import HistoricalChangesMixin
from .models import Debt, Term, Recovery

class TermSerializer(serializers.ModelSerializer):
    """
    Serializer for the Term model.
    Intended to be used nested within the DebtSerializer.
    """
    class Meta:
        model = Term
        fields = [
            'id', 'term_date', 'except_amount', 'pay_amount', 
            'payment_date', 'status'
        ]


class DebtSerializer(serializers.ModelSerializer):
    """
    Serializer for the Debt model.
    Provides a detailed view of a debt, including its associated terms.
    """
    terms = TermSerializer(many=True, read_only=True)
    customer_display_name = serializers.CharField(source='sale.customer.display_name', read_only=True)

    class Meta:
        model = Debt
        fields = [
            'id', 'sale', 'customer_display_name', 'init_amount', 'balance', 'start_date', 'close_date', 
            'monthly_payment', 'month_duration', 'regulation_mode', 'status', 'terms'
        ]


class RecoverySerializer(serializers.ModelSerializer):
    """
    Serializer for the Recovery model.
    Handles the creation of a recovery payment.
    """
    commercial_name = serializers.CharField(source='commercial.get_full_name', read_only=True)

    class Meta:
        model = Recovery
        fields = [
            'id', 'term', 'commercial', 'commercial_name', 'amount', 
            'date', 'payment_mode', 'receipt'
        ]
        read_only_fields = ('date', 'commercial')

    def create(self, validated_data):
        # Automatically set the commercial to the user making the request
        validated_data['commercial'] = self.context['request'].user
        # The model's save method will handle updating Term and Debt balances
        return super().create(validated_data)

"""
Historical Serializers
"""
class HistoricalDebtSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Debt.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 
            'history_user', 'changes', 'sale', 'init_amount', 
            'balance', 'start_date', 'close_date', 'monthly_payment', 
            'month_duration', 'regulation_mode', 'status'
        ]

class HistoricalTermSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Term.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 
            'history_user', 'changes', 'debt', 'term_date', 
            'except_amount', 'pay_amount', 'payment_date', 
            'status'
        ]

class HistoricalRecoverySerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Recovery.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 
            'history_user', 'changes', 'term', 'commercial', 
            'amount', 'date', 'payment_mode', 'receipt'
        ]