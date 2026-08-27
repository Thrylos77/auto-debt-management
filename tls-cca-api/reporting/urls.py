""" reporting/urls.py """

from django.urls import path
from .views import GlobalDashboardView, AgingBalanceView, RecoveryEvolutionView

urlpatterns = [
    path('dashboard/', GlobalDashboardView.as_view(), name='reporting-dashboard'),
    path('aging-balance/', AgingBalanceView.as_view(), name='reporting-aging-balance'),
    path('recovery-evolution/', RecoveryEvolutionView.as_view(), name='reporting-recovery-evolution'),
]