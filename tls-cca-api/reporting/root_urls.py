"""Canonical root-level reporting routes.

These endpoints were historically implemented by ``core``. They now belong to
reporting while keeping their established V1 paths and URL names.
"""

from django.urls import path

from reporting.views import DashboardViewSet, GlobalSearchView


urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("dashboard/summary/", DashboardViewSet.as_view({"get": "summary"}), name="dashboard-summary"),
]
