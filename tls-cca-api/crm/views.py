"""CRM API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import AuditService
from core.events import customer_duplicate_detected
from rbac.policies.permission_policy import AutoPermissionMixin

from .filters import CustomerFilter
from .models import Customer, Portfolio, PortfolioTransfer
from .policies.customer_policy import CustomerPolicy
from .serializers import (
    CustomerBulkDeactivationResponseSerializer,
    CustomerDeactivationPolicySerializer,
    CustomerDuplicateCandidateSerializer,
    CustomerDuplicateCheckResponseSerializer,
    CustomerDuplicateCheckSerializer,
    CustomerLifecycleSerializer,
    CustomerSerializer,
    CustomerTimelineItemSerializer,
    HistoricalCustomerSerializer,
    HistoricalPortfolioSerializer,
    PortfolioAssignSerializer,
    PortfolioSerializer,
    PortfolioTransferInputSerializer,
    PortfolioTransferSerializer,
)
from .services import portfolio_services
from .services.customer_duplicate_service import find_duplicate_candidates
from .services.customer_services import (
    activate_customer,
    archive_customer,
    auto_deactivate_inactive_customers,
    block_customer,
    deactivate_customer,
    get_customers_for_user,
    suspend_customer,
)
from .services.customer_timeline_service import CustomerTimelineService
from .services.inactivity_policy import (
    DEFAULT_CUSTOMER_INACTIVITY_MONTHS,
    get_customer_inactivity_months,
    get_customer_inactivity_threshold,
    set_customer_inactivity_months,
)
from core.throttling import CustomerDuplicateCheckRateThrottle


@extend_schema(tags=["Customers"])
class CustomerViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """Customer CRUD plus explicit lifecycle, duplicate and timeline actions."""

    queryset = Customer.objects.all().order_by("id")
    resource = "customer"
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerFilter
    permission_code_map = {
        "list_all": "list_all",
        "activate": "activate",
        "deactivate": "deactivate",
        "suspend": "suspend",
        "block": "block",
        "archive": "archive",
        "timeline": "timeline",
        "duplicate_check": "duplicate_check",
    }

    def get_queryset(self):
        return get_customers_for_user(self.request.user)

    def get_throttles(self):
        if getattr(self, "action", None) == "duplicate_check":
            return [CustomerDuplicateCheckRateThrottle()]
        return super().get_throttles()

    @action(detail=False, methods=["get"], url_path="list_all")
    def list_all(self, request):
        """List all customers for users holding customer.list_all."""
        all_customers = Customer.objects.all().order_by("id")
        page = self.paginate_queryset(all_customers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(all_customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _transition(self, request, customer, service):
        """Validate transition input and delegate state changes to a service."""
        serializer = CustomerLifecycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return service(
            customer,
            actor=request.user,
            request=request,
            reason=serializer.validated_data.get("reason", ""),
        )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """Activate a prospect, suspended or inactive customer."""
        customer = self.get_object()
        if customer.lifecycle_status == Customer.LIFECYCLE_ACTIVE:
            return Response(
                {"status": "Customer is already active"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._transition(request, customer, activate_customer)
        return Response(
            {"status": "Customer activated"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        """Deactivate an active customer."""
        customer = self.get_object()
        if customer.lifecycle_status == Customer.LIFECYCLE_INACTIVE:
            return Response(
                {"status": "Customer is already inactive"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._transition(request, customer, deactivate_customer)
        return Response(
            {"status": "Customer deactivated"},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=CustomerLifecycleSerializer,
        responses=CustomerSerializer,
    )
    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk=None):
        """Suspend an active customer."""
        customer = self.get_object()
        result = self._transition(request, customer, suspend_customer)
        return Response(
            self.get_serializer(result).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=CustomerLifecycleSerializer,
        responses=CustomerSerializer,
    )
    @action(detail=True, methods=["post"], url_path="block")
    def block(self, request, pk=None):
        """Block a suspended customer."""
        customer = self.get_object()
        result = self._transition(request, customer, block_customer)
        return Response(
            self.get_serializer(result).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=CustomerLifecycleSerializer,
        responses=CustomerSerializer,
    )
    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        """Archive an inactive customer."""
        customer = self.get_object()
        result = self._transition(request, customer, archive_customer)
        return Response(
            self.get_serializer(result).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses=CustomerTimelineItemSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, pk=None):
        """Return the customer's scoped activity timeline."""
        customer = self.get_object()
        if not CustomerPolicy.can_view_timeline(request.user, customer):
            raise PermissionDenied(
                "You do not have permission to view this customer's timeline."
            )

        events = CustomerTimelineService.get_events(
            actor=request.user,
            customer=customer,
        )
        page = self.paginate_queryset(events)
        items = [
            CustomerTimelineItemSerializer(
                CustomerTimelineService.serialize_event(event),
            ).data
            for event in (page if page is not None else events)
        ]
        if page is not None:
            return self.get_paginated_response(items)
        return Response(items, status=status.HTTP_200_OK)

    @extend_schema(
        request=CustomerDuplicateCheckSerializer,
        responses=CustomerDuplicateCheckResponseSerializer,
    )
    @action(detail=False, methods=["post"], url_path="duplicates/check")
    def duplicate_check(self, request):
        """Find possible duplicate customers without modifying stored records."""
        serializer = CustomerDuplicateCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidates = find_duplicate_candidates(**serializer.validated_data)

        AuditService.record(
            actor=request.user,
            category="BUSINESS",
            action="customer.duplicate_check",
            status="success",
            request=request,
            metadata={
                "candidate_count": len(candidates),
            },
        )

        if candidates:
            customer_duplicate_detected.send(
                sender=Customer,
                actor=request.user,
                request=request,
                candidate_ids=[candidate["customer_id"] for candidate in candidates],
            )

        response = CustomerDuplicateCandidateSerializer(
            candidates,
            many=True,
        )
        return Response(
            {"candidates": response.data},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Customers"])
class CustomerBulkDeactivationView(AutoPermissionMixin, APIView):
    """Trigger the configured automatic customer inactivity policy."""

    resource = "customer"
    permission_suffix = "auto_customer_desactivation"
    serializer_class = CustomerBulkDeactivationResponseSerializer

    def get_permission_code_map(self):
        return {"POST": f"{self.permission_suffix}"}

    @extend_schema(
        summary="Auto-deactivate inactive customers",
        request=None,
        responses=CustomerBulkDeactivationResponseSerializer,
    )
    def post(self, request, *args, **kwargs):
        total_checked, deactivated_count = auto_deactivate_inactive_customers()
        response_data = {
            "checked_customers": total_checked,
            "deactivated_customers": deactivated_count,
            "detail": (
                f"Checked {total_checked} active customers. "
                f"Deactivated {deactivated_count} inactive customers."
            ),
        }
        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerDeactivationPolicyView(AutoPermissionMixin, APIView):
    """Read or update the customer inactivity auto-deactivation policy."""

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
    viewsets.GenericViewSet,
):
    """Portfolio CRUD with controlled assignment and transfer actions."""

    queryset = Portfolio.objects.filter(active=True)
    resource = "portfolio"
    serializer_class = PortfolioSerializer
    permission_code_map = {"assign": "assign", "transfer": "transfer"}

    def perform_create(self, serializer):
        portfolio = portfolio_services.create_portfolio_for_commercial(
            self.request.user,
            description=serializer.validated_data.get("description", ""),
        )
        serializer.instance = portfolio

    @extend_schema(
        summary="Assign an existing portfolio to a commercial",
        request=PortfolioAssignSerializer,
        responses=PortfolioSerializer,
    )
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        portfolio = self.get_object()
        serializer = PortfolioAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = portfolio_services.assign_portfolio(
            portfolio,
            to_commercial=serializer.validated_data["commercial"],
            transferred_by=request.user,
            reason=serializer.validated_data.get("reason") or None,
        )
        return Response(self.get_serializer(result).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Transfer a portfolio to another commercial",
        request=PortfolioTransferInputSerializer,
        responses=PortfolioSerializer,
    )
    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        portfolio = self.get_object()
        serializer = PortfolioTransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = portfolio_services.transfer_portfolio(
            portfolio,
            to_commercial=serializer.validated_data["to_commercial"],
            transferred_by=request.user,
            reason=serializer.validated_data.get("reason") or None,
        )
        return Response(self.get_serializer(result).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Customers"])
class CustomerHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only Customer history."""

    queryset = Customer.history.none()
    resource = "customer_history"
    serializer_class = HistoricalCustomerSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return Customer.history.all().order_by("-history_date")


@extend_schema(tags=["Portfolios"])
class PortfolioHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only Portfolio history."""

    queryset = Portfolio.history.none()
    resource = "portfolio_history"
    serializer_class = HistoricalPortfolioSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return Portfolio.history.all().order_by("-history_date")


@extend_schema(tags=["Portfolios"])
class PortfolioTransferViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only immutable PortfolioTransfer journal."""

    queryset = PortfolioTransfer.objects.all().select_related(
        "portfolio",
        "from_commercial",
        "to_commercial",
        "transferred_by",
    )
    resource = "portfolio_transfer"
    serializer_class = PortfolioTransferSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["portfolio", "from_commercial", "to_commercial"]
