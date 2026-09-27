"""config/v1_urls.py"""
from django.urls import include, path


urlpatterns = [
    # The complete Users URL tree is aggregated by users.urls.
    path("", include("users.urls")),
    path("rbac/", include("rbac.urls")),
    path("audit/", include("audit.urls")),
    path("configuration/", include("configuration.urls")),
    path("notifications/", include("notifications.urls")),
    path("crm/", include("crm.urls")),
    path("sales/", include("sales.urls")),
    path("receivables/", include("receivables.urls")),
    path("reporting/", include("reporting.urls")),
]
