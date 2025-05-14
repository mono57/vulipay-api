from typing import Any, Dict, List, Optional, Union

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response


def error_response(
    message: str,
    errors: Optional[Union[Dict, List, Any]] = None,
    error_code: Optional[str] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    response_data = {
        "message": message,
        "error_code": error_code,
        "errors": errors,
    }
    return Response(response_data, status=status_code)


def validation_error_response(
    message: str = "Validation failed",
    errors: Optional[Dict] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    return error_response(
        message=message,
        errors=errors,
        error_code="VALIDATION_ERROR",
        status_code=status_code,
    )
