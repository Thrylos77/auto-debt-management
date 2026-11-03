from django.urls import include, path


urlpatterns = [
    # Global dashboard/search endpoints are now owned by reporting.
    path("", include("reporting.root_urls")),
    path("", include("users.urls")),
    path("rbac/", include("rbac.urls")),
    path("audit/", include("audit.urls")),
    path("configuration/", include("configuration.urls")),
    path("notifications/", include("notifications.urls")),
    path("crm/", include("crm.urls")),
    path("vehicles/", include("vehicles.urls")),
    path("sales/", include("sales.urls")),
    path("receivables/", include("receivables.urls")),
    path("reporting/", include("reporting.urls")),
]
