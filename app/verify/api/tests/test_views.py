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

    @patch("app.verify.models.OTP.generate")
    def test_generate_otp_with_phone_success(self, mock_generate):
        next_otp_allowed_at = timezone.now() + datetime.timedelta(seconds=5)
        mock_otp = OTP(
            identifier="+237698765432",
            code="123456",
            channel="sms",
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
            next_otp_allowed_at=next_otp_allowed_at,
        )

        mock_generate.return_value = {
            "success": True,
            "message": "Verification code sent to +237698765432 via sms.",
            "otp": mock_otp,
            "expires_at": mock_otp.expires_at,
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("expires_at", response.data)
        self.assertIn("next_allowed_at", response.data)
        self.assertEqual(response.data["next_allowed_at"], next_otp_allowed_at)
        mock_generate.assert_called_once()

    @patch("app.verify.models.OTP.generate")
    def test_generate_otp_with_email_success_no_next_allowed(self, mock_generate):
        mock_otp = OTP(
            identifier="test@example.com",
            code="123456",
            channel="email",
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
            next_otp_allowed_at=None,  # No next allowed time for first request
        )

        mock_generate.return_value = {
            "success": True,
            "message": "Verification code sent to test@example.com via email.",
            "otp": mock_otp,
            "expires_at": mock_otp.expires_at,
        }

        response = self.client.post(self.url, self.valid_email_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("expires_at", response.data)
        self.assertNotIn("next_allowed_at", response.data)  # Should not be in response
        mock_generate.assert_called_once()

    @patch("app.verify.models.OTP.generate")
    def test_generate_otp_failure(self, mock_generate):
        mock_generate.return_value = {
            "success": False,
            "message": "Failed to send verification code to +237698765432.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        mock_generate.assert_called_once()

    @patch("app.verify.models.OTP.generate")
    def test_generate_otp_waiting_period(self, mock_generate):
        next_allowed_at = timezone.now() + datetime.timedelta(seconds=30)
        mock_generate.return_value = {
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
        mock_generate.assert_called_once()

    def test_generate_otp_invalid_data(self):
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
            "country_id": self.country.id,
            "country_dial_code": "237",
            "code": "123456",
        }

        self.valid_email_data = {
            "email": "test@example.com",
            "country_id": self.country.id,
            "country_dial_code": "237",
            "code": "123456",
        }

    @patch("app.verify.api.serializers.VerifyOTPSerializer.verify_otp")
    def test_verify_otp_success(self, mock_verify_otp):
        mock_verify_otp.return_value = {
            "success": True,
            "message": "OTP verified successfully.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_verify_otp.assert_called_once()

    @patch("app.verify.api.serializers.VerifyOTPSerializer.verify_otp")
    def test_verify_otp_success_without_user(self, mock_verify_otp):
        mock_verify_otp.return_value = {
            "success": True,
            "message": "OTP verified successfully, but no user found with this identifier.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertNotIn("user", response.data)
        self.assertNotIn("tokens", response.data)
        mock_verify_otp.assert_called_once()

    @patch("app.verify.api.serializers.VerifyOTPSerializer.verify_otp")
    def test_verify_otp_failure(self, mock_verify_otp):
        mock_verify_otp.return_value = {
            "success": False,
            "message": "Invalid code. 2 attempts remaining.",
        }

        response = self.client.post(self.url, self.valid_phone_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        mock_verify_otp.assert_called_once()

    def test_verify_otp_invalid_data(self):
        # Missing email and phone number
        response = self.client.post(
            self.url,
            {
                "code": "123456",
                "country_id": self.country.id,
                "country_dial_code": "237",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Missing country_id
        response = self.client.post(
            self.url,
            {"email": "test@example.com", "country_dial_code": "237", "code": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Missing country_dial_code
        response = self.client.post(
            self.url,
            {
                "email": "test@example.com",
                "country_id": self.country.id,
                "code": "123456",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
