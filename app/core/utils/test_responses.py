"""
Tests for the response utilities.
"""

from django.test import TestCase
from rest_framework import status

from app.core.utils.responses import (
    error_response,
    success_response,
    validation_error_response,
)


class ResponseUtilsTestCase(TestCase):
    """Tests for the response utilities."""

    def test_success_response(self):
        """Test the success_response function."""
        response = success_response(
            message="Success message",
            data={"key": "value"},
            status_code=status.HTTP_201_CREATED,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Success message")
        self.assertEqual(response.data["data"], {"key": "value"})
        self.assertIsNone(response.data["error_code"])
        self.assertIsNone(response.data["errors"])

    def test_success_response_without_data(self):
        """Test the success_response function without data."""
        response = success_response(message="Success message")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Success message")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["error_code"])
        self.assertIsNone(response.data["errors"])

    def test_error_response(self):
        """Test the error_response function."""
        response = error_response(
            message="Error message",
            errors={"field": ["Error detail"]},
            error_code="ERROR_CODE",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Error message")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "ERROR_CODE")
        self.assertEqual(response.data["errors"], {"field": ["Error detail"]})

    def test_error_response_without_error_code(self):
        """Test the error_response function without error_code."""
        response = error_response(
            message="Error message",
            errors={"field": ["Error detail"]},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Error message")
        self.assertIsNone(response.data["data"])
        self.assertIsNone(response.data["error_code"])
        self.assertEqual(response.data["errors"], {"field": ["Error detail"]})

    def test_validation_error_response(self):
        """Test the validation_error_response function."""
        response = validation_error_response(
            message="Validation failed",
            errors={"field": ["Validation error detail"]},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(
            response.data["errors"], {"field": ["Validation error detail"]}
        )

    def test_validation_error_response_with_custom_message(self):
        """Test the validation_error_response function with a custom message."""
        response = validation_error_response(
            message="Custom validation error message",
            errors={"field": ["Validation error detail"]},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Custom validation error message")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(
            response.data["errors"], {"field": ["Validation error detail"]}
        )
