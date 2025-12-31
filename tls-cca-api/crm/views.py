# crm/views.py
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .models import *
from .serializers import *
from .filters import CustomerFilter
from .services.customer_services import (
    activate_customer,
    deactivate_customer,
    auto_deactivate_inactive_customers,
    get_customers_for_user,
)

@extend_schema(tags=["Customers"])
class CustomerViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing customers.
    - Filters by `customer_type`, `is_active`, and `commercial`.
    - Data visibility is based on user role (Admin/Consultant vs. Commercial).
    - Includes actions to activate and deactivate customers.
    """
    queryset = Customer.objects.all().order_by('id') # Base queryset, will be overridden by get_queryset
    resource = "customer"
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerFilter

    def get_queryset(self):
        return get_customers_for_user(self.request.user)
    
    @action(detail=False, methods=['get'], url_path='list_all')
    def list_all(self, request):
        """
        Lists all customers without any filters.
        Accessible only by Admin and Consultant roles.
        """
        all_customers = Customer.objects.all()
        page = self.paginate_queryset(all_customers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(all_customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """
        Activates a customer account.
        """
        customer = self.get_object()
        if customer.is_active:
            return Response({'status': 'Customer is already active'}, status=status.HTTP_400_BAD_REQUEST)
        
        activate_customer(customer)
        return Response({'status': 'Customer activated'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """
        Deactivates a customer account.
        """
        customer = self.get_object()
        if not customer.is_active:
            return Response({'status': 'Customer is already inactive'}, status=status.HTTP_400_BAD_REQUEST)

        deactivate_customer(customer)
        return Response({'status': 'Customer deactivated'}, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerBulkDeactivationView(AutoPermissionMixin, APIView):
    """
    A view to trigger the automatic deactivation of inactive customers.
    This is intended to be used by a scheduled task (e.g., cron job).
    """
    resource = "customer"
    permission_suffix = "auto_customer_desactivation"

    def get_permission_code_map(self):
        return {'POST': f"{self.permission_suffix}"}
    
    @extend_schema(
        summary="Auto-deactivate Inactive Customers",
        responses={
            200: OpenApiParameter(
                name='Deactivation Summary',
                type={'type': 'object', 'properties': {
                    'checked_customers': {'type': 'integer'},
                    'deactivated_customers': {'type': 'integer'},
                    'detail': {'type': 'string'}
                }}
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Triggers the service to find and deactivate customers inactive for over 4 years.
        """
        total_checked, deactivated_count = auto_deactivate_inactive_customers()
        
        response_data = {
            'checked_customers': total_checked,
            'deactivated_customers': deactivated_count,
            'detail': f'Checked {total_checked} active customers. Deactivated {deactivated_count} inactive customers.'
        }
        return Response(response_data, status=status.HTTP_200_OK)

@extend_schema(tags=["Portfolios"])
class PortfolioViewSet(
    AutoPermissionMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for Portfolios.
    Lists only active portfolios by default.
    Deletion is disabled by design. Portfolios should be deactivated instead of deleted
    to preserve historical data and integrity.
    """
    queryset = Portfolio.objects.filter(active=True)
    resource = "portfolio"
    serializer_class = PortfolioSerializer

@extend_schema(tags=["Customers"])
class CustomerHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """

    """
    queryset = Customer.history.all()
    resource = "customer_history"
    serializer_class = HistoricalCustomerSerializer

@extend_schema(tags=["Portfolios"])
class PortfolioHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Portfolio.history.all()
    resource = "portfolio_history"
    serializer_class = HistoricalPortfolioSerializer