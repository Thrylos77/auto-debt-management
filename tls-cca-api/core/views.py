from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from rbac.services.permission_services import AutoPermissionMixin
from .services import stats_services

@extend_schema(tags=["Dashboard"])
class DashboardViewSet(AutoPermissionMixin, viewsets.ViewSet):
    """
    ViewSet for aggregated statistics and dashboard data.
    """
    resource = "dashboard"
    
    @extend_schema(responses={200: dict})
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Returns global KPIs (Sales, Debts, Recoveries) based on the user's scope.
        """
        stats = stats_services.get_global_stats(request.user)
        return Response(stats, status=status.HTTP_200_OK)