""" reporting/serializers.py """

from rest_framework import serializers

class KPISerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.DecimalField(max_digits=20, decimal_places=2)
    count = serializers.IntegerField(required=False)

class AgingBucketSerializer(serializers.Serializer):
    bucket = serializers.CharField(help_text="Ex: '0-30 days', '30-60 days'")
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    count = serializers.IntegerField()

class AgingReportSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    total_overdue = serializers.DecimalField(max_digits=20, decimal_places=2)
    buckets = AgingBucketSerializer(many=True)

class EvolutionPointSerializer(serializers.Serializer):
    period = serializers.DateField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)

class DashboardSummarySerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_debt_initial = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_debt_balance = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_recovered = serializers.DecimalField(max_digits=20, decimal_places=2)
    recovery_rate = serializers.FloatField(help_text="Percentage 0-100")
    active_debtors_count = serializers.IntegerField()