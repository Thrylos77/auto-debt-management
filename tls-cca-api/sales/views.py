# sales/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .models import *
from .serializers import *
from .services import creditsale_services
from .filters import CreditSaleFilter

@extend_schema(tags=["Credit-Sales"])
class CreditSaleViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    resource = "creditsale"
    serializer_class = CreditSaleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CreditSaleFilter

    def get_queryset(self):
        return creditsale_services.get_sales_for_user(self.request.user)

    @extend_schema(request=ChangeCreditSaleStatusSerializer, responses={200: None})
    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        sale = self.get_object()
        serializer = ChangeCreditSaleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        creditsale_services.update_credit_sale_status(sale, serializer.validated_data['status'])
        return Response({'detail': 'Status updated successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='list_all')
    def list_all(self, request):
        """
        Lists all credit sales without restriction (Admin/Consultant view).
        Supports filtering.
        """
        queryset = CreditSale.objects.all()
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(tags=["Credit-Sales"])
class CreditSaleHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = CreditSale.history.all()
    resource = "creditsale_history"
    serializer_class = HistoricalCreditSaleSerializer