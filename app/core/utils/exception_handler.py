"""
Custom exception handler for DRF to provide consistent API responses.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from app.core.utils.responses import error_response, validation_error_response
from app.verify.models import OTPWaitingPeriodError


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if isinstance(exc, OTPWaitingPeriodError):
        return Response(
            {
                "message": exc.detail["message"],
                "data": None,
                "error_code": "RATE_LIMITED",
                "errors": {
                    "waiting_seconds": exc.detail["waiting_seconds"],
                    "next_allowed_at": exc.detail["next_allowed_at"],
                },
            },
            status=exc.status_code,
        )

    if not response:
        if isinstance(exc, DjangoValidationError):
            return validation_error_response(
                message="Validation error",
                errors={"non_field_errors": exc.messages},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        print("response from custom exception handler", response)

        return error_response(
            message="Internal server error",
            error_code="SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = getattr(response, "data", None)
    status_code = response.status_code

    if isinstance(exc, exceptions.ValidationError):
        return validation_error_response(
            message="Validation failed",
            errors=data,
            status_code=status_code,
        )
    elif isinstance(exc, exceptions.NotAuthenticated):
        return error_response(
            message="Authentication required",
            error_code="NOT_AUTHENTICATED",
            status_code=status_code,
        )
    elif isinstance(exc, exceptions.AuthenticationFailed):
        return error_response(
            message="Authentication failed",
            error_code="AUTHENTICATION_FAILED",
            status_code=status_code,
        )
    elif isinstance(exc, exceptions.PermissionDenied):
        return error_response(
            message="Permission denied",
            error_code="PERMISSION_DENIED",
            status_code=status_code,
        )
    elif isinstance(exc, Http404) or isinstance(exc, exceptions.NotFound):
        return error_response(
            message="Resource not found",
            error_code="NOT_FOUND",
            status_code=status_code,
        )
    elif isinstance(exc, exceptions.MethodNotAllowed):
        return error_response(
            message="Method not allowed",
            error_code="METHOD_NOT_ALLOWED",
            status_code=status_code,
        )
    elif isinstance(exc, exceptions.Throttled):
        return error_response(
            message=f"Request throttled. Try again in {exc.wait} seconds.",
            error_code="THROTTLED",
            status_code=status_code,
        )
    else:
        error_detail = str(exc)
        if data and "detail" in data:
            error_detail = data["detail"]

        return error_response(
            message=error_detail,
            error_code="API_ERROR",
            status_code=status_code,
        )
