from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename="customer")
router.register(r'portfolios', PortfolioViewSet, basename="portfolio")

router.register(r'customers-histories', CustomerHistoryViewSet, basename="customer-histories")
router.register(r'portfolios-histories', PortfolioHistoryViewSet, basename="portfolio-histories")

urlpatterns = [
    *router.urls,
    path('customers/bulk-deactivate/', CustomerBulkDeactivationView.as_view(), name='customer-bulk-deactivate'),
]