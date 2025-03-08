import datetime
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.models import AvailableCountry
from app.verify.models import OTP, OTPWaitingPeriodError


class GenerateOTPViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("api:verify:generate_otp")
        self.country_data = {
            "name": "Cameroon",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "",
        }
        self.country = AvailableCountry.objects.create(**self.country_data)

        self.valid_phone_data = {
            "phone_number": "698765432",
            "country_iso_code": "CM",
            "channel": "sms",
        }

        self.valid_email_data = {
            "email": "test@example.com",
            "channel": "email",
        }

    @patch("app.verify.services.OTPService.generate_otp")
    def test_generate_otp_with_phone_success(self, mock_generate_otp):
        # Mock the OTP generation
        mock_generate_otp.return_value = {
            "success": True,
            "message": "Verification code sent to +237698765432 via sms.",
            "otp": OTP(
                identifier="+237698765432",
                code="123456",
                channel="sms",
                expires_at=timezone.now() + datetime.timedelta(minutes=10),
            ),
            "expires_at": timezone.now() + datetime.timedelta(minutes=10),
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_generate_otp.assert_called_once_with("+237698765432", "sms")

    @patch("app.verify.services.OTPService.generate_otp")
    def test_generate_otp_with_email_success(self, mock_generate_otp):
        # Mock the OTP generation
        mock_generate_otp.return_value = {
            "success": True,
            "message": "Verification code sent to test@example.com via email.",
            "otp": OTP(
                identifier="test@example.com",
                code="123456",
                channel="email",
                expires_at=timezone.now() + datetime.timedelta(minutes=10),
            ),
            "expires_at": timezone.now() + datetime.timedelta(minutes=10),
        }

        response = self.client.post(self.url, self.valid_email_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_generate_otp.assert_called_once_with("test@example.com", "email")

    @patch("app.verify.services.OTPService.generate_otp")
    def test_generate_otp_failure(self, mock_generate_otp):
        # Mock the OTP generation failure
        mock_generate_otp.return_value = {
            "success": False,
            "message": "Failed to send verification code to +237698765432.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        mock_generate_otp.assert_called_once_with("+237698765432", "sms")

    @patch("app.verify.services.OTPService.generate_otp")
    def test_generate_otp_waiting_period(self, mock_generate_otp):
        # Mock the OTP generation with waiting period error
        next_allowed_at = timezone.now() + datetime.timedelta(seconds=30)
        mock_generate_otp.return_value = {
            "success": False,
            "message": "Please wait 30 seconds before requesting a new OTP.",
            "waiting_seconds": 30,
            "next_allowed_at": next_allowed_at,
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(response.data["success"])
        self.assertEqual(
            response.data["message"],
            "Please wait 30 seconds before requesting a new OTP.",
        )
        self.assertEqual(response.data["waiting_seconds"], 30)
        self.assertEqual(response.data["next_allowed_at"], next_allowed_at)
        mock_generate_otp.assert_called_once_with("+237698765432", "sms")

    def test_generate_otp_invalid_data(self):
        # Missing both phone_number and email
        response = self.client.post(self.url, {"channel": "sms"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])


class VerifyOTPViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("api:verify:verify_otp")
        self.country_data = {
            "name": "Cameroon",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "",
        }
        self.country = AvailableCountry.objects.create(**self.country_data)

        self.valid_phone_data = {
            "phone_number": "698765432",
            "country_iso_code": "CM",
            "code": "123456",
        }

        self.valid_email_data = {
            "email": "test@example.com",
            "code": "123456",
        }

    @patch("app.verify.services.OTPService.verify_otp")
    def test_verify_otp_success(self, mock_verify_otp):
        # Mock the OTP verification
        mock_verify_otp.return_value = {
            "success": True,
            "message": "OTP verified successfully.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_verify_otp.assert_called_once_with("+237698765432", "123456")

    @patch("app.verify.services.OTPService.verify_otp")
    def test_verify_otp_failure(self, mock_verify_otp):
        # Mock the OTP verification failure
        mock_verify_otp.return_value = {
            "success": False,
            "message": "Invalid code. 2 attempts remaining.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        mock_verify_otp.assert_called_once_with("+237698765432", "123456")

    def test_verify_otp_invalid_data(self):
        # Missing both phone_number and email
        response = self.client.post(self.url, {"code": "123456"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
