
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

class TermViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Term.objects.all()
    resource = "term"

class RecoveryViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Recovery.objects.all()
    resource = "recovery"

class ReceivablesHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """