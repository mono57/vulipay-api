"""
Tests for the custom exception handler.
"""

from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import TestCase
from rest_framework import exceptions, status
from rest_framework.views import exception_handler as drf_exception_handler

from app.core.utils.exception_handler import exception_handler


class ExceptionHandlerTestCase(TestCase):
    """Tests for the custom exception handler."""

    def test_validation_error(self):
        """Test handling of ValidationError."""
        exc = exceptions.ValidationError({"field": ["Error"]})
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(response.data["errors"], {"field": ["Error"]})

    def test_not_authenticated(self):
        """Test handling of NotAuthenticated."""
        exc = exceptions.NotAuthenticated()
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Authentication required")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "NOT_AUTHENTICATED")
        self.assertIsNone(response.data["errors"])

    def test_authentication_failed(self):
        """Test handling of AuthenticationFailed."""
        exc = exceptions.AuthenticationFailed("Invalid token")
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Authentication failed")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "AUTHENTICATION_FAILED")
        self.assertIsNone(response.data["errors"])

    def test_permission_denied(self):
        """Test handling of PermissionDenied."""
        exc = exceptions.PermissionDenied()
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Permission denied")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "PERMISSION_DENIED")
        self.assertIsNone(response.data["errors"])

    def test_not_found(self):
        """Test handling of NotFound."""
        exc = exceptions.NotFound()
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Resource not found")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "NOT_FOUND")
        self.assertIsNone(response.data["errors"])

    def test_http404(self):
        """Test handling of Http404."""
        exc = Http404()
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["message"], "Resource not found")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "NOT_FOUND")
        self.assertIsNone(response.data["errors"])

    def test_method_not_allowed(self):
        """Test handling of MethodNotAllowed."""
        exc = exceptions.MethodNotAllowed("POST")
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data["message"], "Method not allowed")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "METHOD_NOT_ALLOWED")
        self.assertIsNone(response.data["errors"])

    def test_throttled(self):
        """Test handling of Throttled."""
        exc = exceptions.Throttled(wait=60)
        context = {}
        response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            response.data["message"], "Request throttled. Try again in 60 seconds."
        )
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "THROTTLED")
        self.assertIsNone(response.data["errors"])

    def test_django_validation_error(self):
        """Test handling of Django ValidationError."""
        exc = DjangoValidationError(["Error 1", "Error 2"])
        context = {}

        # Mock DRF's exception handler to return None (as it would for a Django exception)
        with patch(
            "app.core.utils.exception_handler.drf_exception_handler", return_value=None
        ):
            response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation error")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(
            response.data["errors"], {"non_field_errors": ["Error 1", "Error 2"]}
        )

    def test_unhandled_exception(self):
        """Test handling of unhandled exceptions."""
        exc = Exception("Something went wrong")
        context = {}

        # Mock DRF's exception handler to return None (as it would for an unhandled exception)
        with patch(
            "app.core.utils.exception_handler.drf_exception_handler", return_value=None
        ):
            response = exception_handler(exc, context)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], "Internal server error")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "SERVER_ERROR")
        self.assertIsNone(response.data["errors"])
