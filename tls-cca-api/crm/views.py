# crm/views.py
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import *
from .serializers import *

import os

class CustomerViewSet(viewsets.ModelViewSet):
    """

    """
    queryset = Customer.objects.all()
    resource = "customer"
    serializer_class = CustomerSerializer

class PortfolioViewSet(viewsets.ModelViewSet):
    """
    
    """
    queryset = Portfolio.objects.all()
    resource = "portfolio"
    serializer_class = PortfolioSerializer


class CustomerHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Customer.history.all()
    resource = "customer_history"
    serializer_class = HistoricalCustomerSerializer


class PortfolioHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """
    queryset = Portfolio.history.all()
    resource = "portfolio_history"
    serializer_class = HistoricalPortfolioSerializer