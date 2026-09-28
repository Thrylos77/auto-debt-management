"""Core platform views that do not depend on business applications."""

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.response import Response


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
