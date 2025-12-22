# sales/views.py
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .models import *
from .serializers import *

@extend_schema(tags=["Credit-Sales"])
class CreditSaleViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    queryset = CreditSale.objects.all()
    resource = "creditsale"
    serializer_class = CreditSaleSerializer

@extend_schema(tags=["Credit-Sales"])
class CreditSaleHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = CreditSale.history.all()
    resource = "creditsale_history"
    serializer_class = HistoricalCreditSaleSerializer