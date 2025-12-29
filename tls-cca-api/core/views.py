from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .services import stats_services, search_services

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

@extend_schema(tags=["Search"])
class GlobalSearchView(views.APIView):
    """
    Global search endpoint returning grouped results (Sales, Debts, etc.).
    """
    permission_classes = [] # Géré manuellement ou via IsAuthenticated par défaut dans settings

    @extend_schema(
        parameters=[OpenApiParameter(name='q', description='Search query', required=True, type=str)],
        responses={200: dict}
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        results = search_services.search_global(request.user, query)
        return Response(results, status=status.HTTP_200_OK)