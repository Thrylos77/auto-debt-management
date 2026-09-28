""" crm/views.py """

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from rbac.policies.permission_policy import AutoPermissionMixin
from .models import *
from .serializers import *
from .filters import CustomerFilter
from .services.customer_services import (
    activate_customer,
    deactivate_customer,
    auto_deactivate_inactive_customers,
    get_customers_for_user,
)
from .services import portfolio_services
from .services.inactivity_policy import (
    DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
    get_customer_inactivity_months,
    get_customer_inactivity_threshold,
    set_customer_inactivity_months,
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
    # Custom actions (list_all / activate / deactivate) require dedicated
    # permission codes: customer.list_all, customer.activate, customer.deactivate.
    permission_code_map = {'list_all': 'list_all', 'activate': 'activate', 'deactivate': 'deactivate'}

    def get_queryset(self):
        return get_customers_for_user(self.request.user)
    
    @action(detail=False, methods=['get'], url_path='list_all')
    def list_all(self, request):
        """
        Lists all customers without any filters.
        Accessible only by Admin and Consultant roles.
        """
        all_customers = Customer.objects.all().order_by("id")
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
        
        activate_customer(
            customer,
            actor=request.user,
            request=request,
        )
        return Response({'status': 'Customer activated'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """
        Deactivates a customer account.
        """
        customer = self.get_object()
        if not customer.is_active:
            return Response({'status': 'Customer is already inactive'}, status=status.HTTP_400_BAD_REQUEST)

        deactivate_customer(
            customer,
            actor=request.user,
            request=request,
        )
        return Response({'status': 'Customer deactivated'}, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerBulkDeactivationView(AutoPermissionMixin, APIView):
    """
    A view to trigger the automatic deactivation of inactive customers.
    This is intended to be used by a scheduled task (e.g., cron job).
    """
    resource = "customer"
    permission_suffix = "auto_customer_desactivation"
    serializer_class = CustomerBulkDeactivationResponseSerializer

    def get_permission_code_map(self):
        return {'POST': f"{self.permission_suffix}"}
    
    @extend_schema(
        summary="Auto-deactivate inactive customers",
        request=None,
        responses=CustomerBulkDeactivationResponseSerializer,
    )
    def post(self, request, *args, **kwargs):
        """
        Triggers the service to find and deactivate customers inactive for over
        the configured inactivity period (default 4 years).
        """
        total_checked, deactivated_count = auto_deactivate_inactive_customers()
        
        response_data = {
            'checked_customers': total_checked,
            'deactivated_customers': deactivated_count,
            'detail': f'Checked {total_checked} active customers. Deactivated {deactivated_count} inactive customers.'
        }
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerDeactivationPolicyView(AutoPermissionMixin, APIView):
    """
    Read/update the customer inactivity auto-deactivation policy.
    Access is controlled by the canonical configuration permissions.

    - `inactivity_months` (default **48** = 4 years): the exact inactivity
      duration in months after which an inactive customer is deactivated.
    """
    resource = "configuration"
    serializer_class = CustomerDeactivationPolicySerializer
    permission_code_map = {
        "GET": "view",
        "PUT": "update",
        "PATCH": "update",
    }

    @extend_schema(
        summary="Get customer inactivity policy",
        responses=CustomerDeactivationPolicySerializer,
    )
    def get(self, request, *args, **kwargs):
        months = get_customer_inactivity_months()
        data = {
            "inactivity_months": months,
            "default_inactivity_months": DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
            "threshold_date": get_customer_inactivity_threshold().isoformat(),
        }
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update customer inactivity policy (admin only)",
        request=CustomerDeactivationPolicySerializer,
        responses=CustomerDeactivationPolicySerializer,
    )
    def put(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        months = serializer.validated_data["inactivity_months"]

        set_customer_inactivity_months(
            months,
            actor=request.user,
            request=request,
        )

        data = {
            "inactivity_months": months,
            "default_inactivity_months": DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
            "threshold_date": get_customer_inactivity_threshold().isoformat(),
        }
        return Response(data, status=status.HTTP_200_OK)

    patch = put

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
    # The `assign` and `transfer` actions require dedicated permissions
    # (portfolio.assign / portfolio.transfer) defined in the RBAC permissions config.
    permission_code_map = {'assign': 'assign', 'transfer': 'transfer'}

    def perform_create(self, serializer):
        portfolio = portfolio_services.create_portfolio_for_commercial(
            self.request.user,
            description=serializer.validated_data.get("description", ""),
        )
        serializer.instance = portfolio

    @extend_schema(
        summary="Assign an existing portfolio to a commercial",
        description=(
            "Assigns this portfolio to the given active commercial. Records a "
            "PortfolioTransfer journal entry with the provided reason."
        ),
        request=PortfolioAssignSerializer,
        responses=PortfolioSerializer,
    )
    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """
        Assigns an existing portfolio to an active commercial.
        Body: { "commercial": <id>, "reason": "optional" }
        """
        portfolio = self.get_object()
        serializer = PortfolioAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        portfolio_services.assign_portfolio(
            portfolio,
            to_commercial=serializer.validated_data['commercial'],
            transferred_by=request.user,
            reason=serializer.validated_data.get('reason') or None,
        )
        return Response(self.get_serializer(portfolio).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Transfer a portfolio to another commercial",
        description=(
            "Transfers this portfolio to the given active commercial "
            "(e.g. when its current owner is leaving). Records a journal entry."
        ),
        request=PortfolioTransferInputSerializer,
        responses=PortfolioSerializer,
    )
    @action(detail=True, methods=['post'], url_path='transfer')
    def transfer(self, request, pk=None):
        """
        Transfers this portfolio to an active commercial (leaving commercial scenario).
        Body: { "to_commercial": <id>, "reason": "optional" }
        """
        portfolio = self.get_object()
        serializer = PortfolioTransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        portfolio_services.transfer_portfolio(
            portfolio,
            to_commercial=serializer.validated_data['to_commercial'],
            transferred_by=request.user,
            reason=serializer.validated_data.get('reason') or None,
        )
        return Response(self.get_serializer(portfolio).data, status=status.HTTP_200_OK)

@extend_schema(tags=["Customers"])
class CustomerHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """

    """
    queryset = Customer.history.none()
    resource = "customer_history"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return Customer.history.all().order_by("-history_date")
    serializer_class = HistoricalCustomerSerializer

@extend_schema(tags=["Portfolios"])
class PortfolioHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Portfolio.history.none()
    resource = "portfolio_history"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return Portfolio.history.all().order_by("-history_date")
    serializer_class = HistoricalPortfolioSerializer

@extend_schema(tags=["Portfolios"])
class PortfolioTransferViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only view of the PortfolioTransfer journal (assignment/transfer audit trail).
    Filterable by `portfolio`, `from_commercial` and `to_commercial`.
    """
    queryset = PortfolioTransfer.objects.all().select_related(
        'portfolio', 'from_commercial', 'to_commercial', 'transferred_by'
    )
    resource = "portfolio_transfer"
    serializer_class = PortfolioTransferSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['portfolio', 'from_commercial', 'to_commercial']