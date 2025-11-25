
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import *
from .serializers import *

import os

class CreditSaleViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = CreditSale.objects.all()
    resource = "creditsale"

class CreditSaleHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = CreditSale.history.all()
    resource = "creditsalehistory"
    serializer_class = HistoricalCreditSaleSerializer