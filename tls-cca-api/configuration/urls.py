"""Configuration API routes."""

from django.urls import path

from configuration.views import (
    ConfigurationSettingDetailView,
    ConfigurationSettingListView,
)

urlpatterns = [
    path("settings/", ConfigurationSettingListView.as_view(), name="configuration-settings-list",),
    path("settings/<str:key>/", ConfigurationSettingDetailView.as_view(), name="configuration-setting-detail",),
]
