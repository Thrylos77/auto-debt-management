from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'debts', DebtViewSet, basename="debt")
router.register(r'Terms', TermViewSet, basename="term")
router.register(r'recoveries', RecoveryViewSet, basename="recovery")

router.register(r'debts-histories', DebtHistoryViewSet, basename="debt-histories")
router.register(r'terms-histories', TermHistoryViewSet, basename="term-histories")
router.register(r'recoveries-histories', RecoveryHistoryViewSet, basename="recovery-histories")


urlpatterns = [
    path('debts/update-status/', DebtStatusUpdateView.as_view(), name='debt-status-update'),
    *router.urls
]