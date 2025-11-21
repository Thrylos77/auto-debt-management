from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'physicals', PhysicalPersonViewSet, basename="physical")
router.register(r'morals', MoralPersonViewSet, basename="moral")
router.register(r'customers', CustomerViewSet, basename="customer")
router.register(r'portfolios', PortfolioViewSet, basename="portfolio")

router.register(r'crm-histories', CrmHistoryViewSet, basename="crm-histories")

urlpatterns = [
    router.urls
]