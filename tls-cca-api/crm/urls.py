""" CRM Urls"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename="customer")
router.register(r'portfolios', PortfolioViewSet, basename="portfolio")
router.register(r'portfolio-transfers', PortfolioTransferViewSet, basename="portfolio-transfer")

router.register(r'customers-histories', CustomerHistoryViewSet, basename="customer-histories")
router.register(r'portfolios-histories', PortfolioHistoryViewSet, basename="portfolio-histories")

urlpatterns = [
    # Concrete paths must be declared BEFORE router urls so that
    # "customers/bulk-deactivate/" and "customers/deactivation-policy/" are not
    # captured by the router's "customers/{pk}/" detail route.
    path('customers/bulk-deactivate/', CustomerBulkDeactivationView.as_view(), name='customer-bulk-deactivate'),
    path('customers/deactivation-policy/', CustomerDeactivationPolicyView.as_view(), name='customer-deactivation-policy'),
    *router.urls,
]