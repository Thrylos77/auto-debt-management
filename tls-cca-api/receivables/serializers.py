# receivables/serializers.py
from rest_framework import serializers

from core.mixins.serializers import HistoricalChangesMixin
from .models import Debt, Term, Recovery
from .services import recovery_services

class TermSerializer(serializers.ModelSerializer):
    """
    Serializer for the Term model.
    Intended to be used nested within the DebtSerializer.
    """
    class Meta:
        model = Term
        fields = [
            'id', 'term_date', 'except_amount', 'pay_amount', 
            'payment_date', 'term_status'
        ]

        read_only_fields = ('term_date', 'except_amount')


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
            'monthly_payment', 'month_duration', 'regulation_mode', 'debt_status', 'terms'
        ]

        read_only_fields = ('terms', 'sale', 'customer_display_name', 'init_amount', 'balance')


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
            'recovery_date', 'payment_mode', 'receipt'
        ]
        read_only_fields = ('recovery_date', 'commercial', 'commercial_name')

    def create(self, validated_data):
        commercial = self.context['request'].user
        # Delegate creation to the recovery service to handle business logic
        return recovery_services.create_recovery(
            commercial=commercial,
            **validated_data
        )

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
            'month_duration', 'regulation_mode', 'debt_status'
        ]

class HistoricalTermSerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Term.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 
            'history_user', 'changes', 'debt', 'term_date', 
            'except_amount', 'pay_amount', 'payment_date', 
            'term_status'
        ]

class HistoricalRecoverySerializer(serializers.ModelSerializer, HistoricalChangesMixin):
    class Meta:
        model = Recovery.history.model
        fields = [
            'history_id', 'history_date', 'history_type_display', 
            'history_user', 'changes', 'term', 'commercial', 
            'amount', 'recovery_date', 'payment_mode', 'receipt'
        ]