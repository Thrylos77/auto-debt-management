from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from core.services import stats_services

class StatsMixin:
    """
    Mixin to add 'stats' and 'timeline' actions to a ViewSet.
    The ViewSet must define:
    - stats_aggregates: dict of aggregation expressions
    - timeline_date_field: str (field name for grouping)
    - timeline_amount_field: str (field name for summing)
    - timeline_amount_alias: str (optional, default 'total_amount')
    """
    stats_aggregates = {}
    timeline_date_field = None
    timeline_amount_field = None
    timeline_amount_alias = 'total_amount'

    @extend_schema(summary="Get aggregated stats for filtered list")
    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        stats = stats_services.calculate_stats(queryset, self.stats_aggregates)
        return Response(stats)

    @extend_schema(summary="Get evolution over time")
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        data = stats_services.calculate_timeline(
            queryset, 
            self.timeline_date_field, 
            self.timeline_amount_field,
            self.timeline_amount_alias
        )
        return Response(list(data))