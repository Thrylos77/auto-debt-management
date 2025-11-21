
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import *
from .serializers import *

import os

class PhysicalPersonViewSet(viewsets.ModelViewSet):
    """

    """

class MoralPersonViewSet(viewsets.ModelViewSet):
    """

    """

class CustomerViewSet(viewsets.ModelViewSet):
    """

    """

class PortfolioViewSet(viewsets.ModelViewSet):
    """
    
    """

class CrmHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    
    """