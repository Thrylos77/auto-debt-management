"""Reporting and platform-wide query views."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rbac.policies.permission_policy import AutoPermissionMixin
from reporting.serializers import (
    AgingReportSerializer,
    DashboardSummarySerializer,
    EvolutionPointSerializer,
    GlobalSearchResponseSerializer,
)
from reporting.services import reporting_services
from reporting.services.dashboard_services import get_dashboard_stats
from reporting.services.search_services import search_global


@extend_schema(tags=["Dashboard"])
class DashboardViewSet(AutoPermissionMixin, viewsets.ViewSet):
    """Expose dashboard KPIs formerly owned by the core module."""

    resource = "dashboard"
    permission_code_map = {"summary": "summary"}

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        data = get_dashboard_stats(request.user)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=["Search"])
class GlobalSearchView(views.APIView):
    """Federated search across customers, sales and receivables."""

    serializer_class = GlobalSearchResponseSerializer

    @extend_schema(
        summary="Global search",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search text. At least two characters are required.",
            ),
        ],
        responses=GlobalSearchResponseSerializer,
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        return Response(search_global(request.user, query))


@extend_schema(tags=["Reporting"])
class GlobalDashboardView(AutoPermissionMixin, views.APIView):
    """Provide unrestricted reporting KPIs for authorized reporting users."""

    serializer_class = DashboardSummarySerializer

    resource = "reporting_dashboard"

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request):
        data = reporting_services.get_global_dashboard_stats()
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)


@extend_schema(tags=["Reporting"])
class AgingBalanceView(AutoPermissionMixin, views.APIView):
    """Generate the receivables aging report."""

    serializer_class = AgingReportSerializer

    resource = "reporting_aging"

    @extend_schema(responses=AgingReportSerializer)
    def get(self, request):
        data = reporting_services.get_aging_balance_report()
        return Response(data)


@extend_schema(tags=["Reporting"])
class RecoveryEvolutionView(AutoPermissionMixin, views.APIView):
    """Show monthly recovery evolution."""

    serializer_class = EvolutionPointSerializer

    resource = "reporting_evolution"

    @extend_schema(responses=EvolutionPointSerializer(many=True))
    def get(self, request):
        data = reporting_services.get_recovery_evolution()
        return Response(data)
