# receivables/views.py
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, OpenApiParameter

from rbac.services.permission_services import AutoPermissionMixin
from .models import *
from .serializers import *

@extend_schema(tags=["Debts"])
class DebtViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Debt.objects.all()
    resource = "debt"
    serializer_class = DebtSerializer

@extend_schema(tags=["Terms"])
class TermViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Term.objects.all()
    resource = "term"
    serializer_class = TermSerializer


@extend_schema(tags=["Recoveries"])
class RecoveryViewSet(AutoPermissionMixin, viewsets.ModelViewSet):
    """

    """
    queryset = Recovery.objects.all()
    resource = "recovery"
    serializer_class = RecoverySerializer

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