# receivables/views.py
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import *
from .serializers import *

import os

class DebtViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Debt.objects.all()
    resource = "debt"
    serializer_class = DebtSerializer


class TermViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Term.objects.all()
    resource = "term"
    serializer_class = TermSerializer

class RecoveryViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Recovery.objects.all()
    resource = "recovery"
    serializer_class = RecoverySerializer

class DebtHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Debt.history.all()
    resource = "debt_history"
    serializer_class = HistoricalDebtSerializer

class TermHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Term.history.all()
    resource = "term_history"
    serializer_class = HistoricalTermSerializer

class RecoveryHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Recovery.history.all()
    resource = "recovery_history"
    serializer_class = HistoricalRecoverySerializer