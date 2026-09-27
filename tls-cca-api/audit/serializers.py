from rest_framework import serializers
from .models import AuditEvent

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ("id", "occurred_at", "actor_user", "category", "action", "resource_type", "resource_id", "status", "reason", "ip_address", "user_agent", "correlation_id", "metadata")
        read_only_fields = fields
