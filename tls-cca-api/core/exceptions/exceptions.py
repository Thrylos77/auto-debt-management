"""Application-level API exceptions."""

from rest_framework.exceptions import APIException


class APIError(APIException):
    status_code = 400
    default_detail = "Request could not be processed."
    default_code = "api_error"


class ServiceUnavailableError(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"
