"""config/urls.py"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from users.views import LegacyTokenObtainPairView, LogoutView, RefreshView, VerifyTokenView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/health/", include("core.health_urls")),

    # Versioned API: new endpoints always live here.
    path("api/v1/", include("config.v1_urls")),

    # Legacy aliases: same views/services, no duplicate implementation.
    path("api/core/", include("core.urls")),
    path("api/users/", include("users.legacy_urls")),
    path("api/", include("rbac.urls")),
    path("api/crm/", include("crm.urls")),
    path("api/sales/", include("sales.urls")),
    path("api/receivables/", include("receivables.urls")),
    path("api/reporting/", include("reporting.urls")),
    path("api/audit/", include("audit.urls")),
    path("api/token/", LegacyTokenObtainPairView.as_view(), name="legacy-token-obtain"),
    path("api/token/logout/", LogoutView.as_view(), name="legacy-token-logout"),
    path("api/token/refresh/", RefreshView.as_view(), name="legacy-token-refresh"),
    path("api/token/verify/", VerifyTokenView.as_view(), name="legacy-token-verify"),
]
