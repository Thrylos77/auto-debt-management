from drf_spectacular.utils import extend_schema
from rest_framework import generics

from rbac.policies.permission_policy import AutoPermissionMixin
from .models import AuditEvent
from .serializers import AuditEventSerializer


@extend_schema(tags=["Audit"])
class AuditEventListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = AuditEventSerializer
    resource = "audit"
    permission_code_map = {"GET": "list"}

    def get_queryset(self):
        qs = AuditEvent.objects.select_related("actor_user").all()
        for field in ("category", "action", "status", "resource_type", "resource_id", "actor_user"):
            value = self.request.query_params.get(field)
            if value:
                qs = qs.filter(**{field: value})
        return qs


@extend_schema(tags=["Audit"])
class AuditEventDetailView(AutoPermissionMixin, generics.RetrieveAPIView):
    queryset = AuditEvent.objects.select_related("actor_user").all()
    serializer_class = AuditEventSerializer
    resource = "audit"
    permission_code_map = {"GET": "view"}
