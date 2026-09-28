"""Early request-size protection for the public API."""

from django.conf import settings
from django.http import JsonResponse


class RequestBodySizeLimitMiddleware:
    """Reject oversized API request bodies before DRF parses them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH"}:
            content_length = request.META.get("CONTENT_LENGTH")
            if content_length:
                try:
                    size = int(content_length)
                except (TypeError, ValueError):
                    size = None

                max_bytes = int(getattr(settings, "API_MAX_REQUEST_BYTES", 0))
                if size is not None and max_bytes > 0 and size > max_bytes:
                    return JsonResponse(
                        {"detail": "Request body too large."},
                        status=413,
                    )

        return self.get_response(request)
