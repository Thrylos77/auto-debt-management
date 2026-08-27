""" reporting/views.py """

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from rbac.services.permission_services import AutoPermissionMixin
from .serializers import DashboardSummarySerializer, AgingReportSerializer, EvolutionPointSerializer
from .services import reporting_services

@extend_schema(tags=["Reporting"])
class GlobalDashboardView(AutoPermissionMixin, APIView):
    """
    Provides high-level KPIs for the dashboard:
    - Total Sales Volume
    - Total Debt Initial Amount
    - Current Total Balance (Outstanding)
    - Total Recovered Amount
    - Global Recovery Rate
    """
    resource = "reporting_dashboard"

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request):
        data = reporting_services.get_global_dashboard_stats()
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)

@extend_schema(tags=["Reporting"])
class AgingBalanceView(AutoPermissionMixin, APIView):
    """
    Generates the Aging Report (Balance Âgée).
    Groups unpaid terms by overdue duration:
    - Not Due (Future)
    - 0-30 days overdue
    - 30-60 days overdue
    - 60-90 days overdue
    - 90+ days overdue
    """
    resource = "reporting_aging"

    @extend_schema(responses=AgingReportSerializer)
    def get(self, request):
        data = reporting_services.get_aging_balance_report()
        return Response(data)

@extend_schema(tags=["Reporting"])
class RecoveryEvolutionView(AutoPermissionMixin, APIView):
    """
    Shows the evolution of recoveries (cash collected) over time, grouped by month.
    """
    resource = "reporting_evolution"

    @extend_schema(responses=EvolutionPointSerializer(many=True))
    def get(self, request):
        data = reporting_services.get_recovery_evolution()
        return Response(data)
