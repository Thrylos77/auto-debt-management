# sales/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .models import *
from .serializers import *
from .services import creditsale_services

@extend_schema(tags=["Credit-Sales"])
class CreditSaleViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    queryset = CreditSale.objects.all()
    resource = "creditsale"
    serializer_class = CreditSaleSerializer

    @extend_schema(request=ChangeCreditSaleStatusSerializer, responses={200: None})
    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        sale = self.get_object()
        serializer = ChangeCreditSaleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        creditsale_services.update_credit_sale_status(sale, serializer.validated_data['status'])
        return Response({'detail': 'Status updated successfully.'}, status=status.HTTP_200_OK)

@extend_schema(tags=["Credit-Sales"])
class CreditSaleHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = CreditSale.history.all()
    resource = "creditsale_history"
    serializer_class = HistoricalCreditSaleSerializer