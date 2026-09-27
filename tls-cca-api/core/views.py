"""Core health and legacy dashboard/search views."""

from django.db import connection
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.serializers import GlobalSearchResponseSerializer
from core.services import search_services, stats_services
from rbac.policies.permission_policy import AutoPermissionMixin


class LivenessView(views.APIView):
    permission_classes = []

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ReadinessView(views.APIView):
    permission_classes = []

    @extend_schema(responses={200: dict, 503: dict})
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return Response(
                {"status": "not_ready", "checks": {"database": "down"}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {"status": "ready", "checks": {"database": "ok"}},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Dashboard"])
class DashboardViewSet(AutoPermissionMixin, viewsets.ViewSet):
    resource = "dashboard"
    permission_code_map = {"summary": "summary"}

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        stats = stats_services.get_global_stats(request.user)
        return Response(stats, status=status.HTTP_200_OK)


@extend_schema(tags=["Search"])
class GlobalSearchView(views.APIView):
    """
    Federated search endpoint across customers, credit sales and debts.

    The explicit response serializer keeps the endpoint fully represented in
    the generated OpenAPI document instead of forcing drf-spectacular to
    guess the response shape from an APIView.
    """

    @extend_schema(
        summary="Global search",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search text. At least two characters are required.",
            ),
        ],
        responses=GlobalSearchResponseSerializer,
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        results = search_services.search_global(request.user, query)
        return Response(results, status=status.HTTP_200_OK)
