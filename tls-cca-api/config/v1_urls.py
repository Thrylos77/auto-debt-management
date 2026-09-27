from django.urls import include, path

urlpatterns = [
    path("auth/", include("users.auth_urls")),
    path("users/", include("users.urls")),
    path("rbac/", include("rbac.urls")),
    path("crm/", include("crm.urls")),
    path("sales/", include("sales.urls")),
    path("receivables/", include("receivables.urls")),
    path("reporting/", include("reporting.urls")),
]
