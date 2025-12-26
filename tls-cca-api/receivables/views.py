# receivables/views.py
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from rbac.services.permission_services import AutoPermissionMixin
from core.mixins import StatsMixin
from .models import *
from .serializers import *
from .filters import DebtFilter, TermFilter, RecoveryFilter
from .services import debt_services

# Debts viewsets
@extend_schema(tags=["Debts"])
class DebtViewSet(AutoPermissionMixin, StatsMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Debt.objects.all()
    resource = "debt"
    serializer_class = DebtSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DebtFilter

    stats_aggregates = {
        'total_initial_amount': Coalesce(Sum('init_amount'), 0.0),
        'total_balance': Coalesce(Sum('balance'), 0.0),
        'count': Count('id')
    }
    timeline_date_field = 'start_date'
    timeline_amount_field = 'init_amount'
    timeline_amount_alias = 'total_amount'

@extend_schema(tags=["Debts"])
class DebtStatusUpdateView(AutoPermissionMixin, views.APIView):
    """
    View to trigger the daily update of Debt and Term statuses (ONGOING, OVERDUE).
    Should be called by a scheduler.
    """
    resource = "debt"
    permission_suffix = "update_status" # Requires permission: debt.update_status

    def get_permission_code_map(self):
        return {'POST': f"{self.permission_suffix}"}

    def post(self, request, *args, **kwargs):
        updated_count = debt_services.update_financial_statuses()
        return Response({'detail': f'Statuses updated. {updated_count} debts marked as overdue.'}, status=status.HTTP_200_OK)

# Terms viewsets
@extend_schema(tags=["Terms"])
class TermViewSet(AutoPermissionMixin, StatsMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Term.objects.all()
    resource = "term"
    serializer_class = TermSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TermFilter

    stats_aggregates = {
        'total_expected': Coalesce(Sum('except_amount'), 0.0),
        'total_paid': Coalesce(Sum('pay_amount'), 0.0),
        'count': Count('id')
    }
    timeline_date_field = 'term_date'
    timeline_amount_field = 'except_amount'
    timeline_amount_alias = 'total_expected'

# Recoveries viewsets
@extend_schema(tags=["Recoveries"])
class RecoveryViewSet(AutoPermissionMixin, StatsMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Recovery.objects.all()
    resource = "recovery"
    serializer_class = RecoverySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecoveryFilter

    stats_aggregates = {
        'total_collected': Coalesce(Sum('amount'), 0.0),
        'count': Count('id')
    }
    timeline_date_field = 'recovery_date'
    timeline_amount_field = 'amount'
    timeline_amount_alias = 'total_collected'


""" Historical ViewSets """
@extend_schema(tags=["Debts"])
class DebtHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Debt.history.all()
    resource = "debt_history"
    serializer_class = HistoricalDebtSerializer

@extend_schema(tags=["Terms"])
class TermHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Term.history.all()
    resource = "term_history"
    serializer_class = HistoricalTermSerializer

@extend_schema(tags=["Recoveries"])
class RecoveryHistoryViewSet(AutoPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Recovery.history.all()
    resource = "recovery_history"
    serializer_class = HistoricalRecoverySerializer