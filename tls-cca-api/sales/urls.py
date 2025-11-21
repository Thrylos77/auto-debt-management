from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'creditsales', CreditSaleViewSet, basename="creditsale")

router.register(r'creditsale-histories', CreditSaleHistoryViewSet, basename="creditsale-histories")

urlpatterns = [
    router.urls
]