from unittest.mock import Mock, patch

from django.test import TestCase

from app.accounts.models import AvailableCountry
from app.verify.api.serializers import GenerateOTPSerializer, VerifyOTPSerializer


class GenerateOTPSerializerTestCase(TestCase):
    def setUp(self):
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

    def test_validate_with_phone_number(self):
        serializer = GenerateOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["identifier"], "+237698765432")

    def test_validate_with_email(self):
        serializer = GenerateOTPSerializer(data=self.valid_email_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["identifier"], "test@example.com")

    def test_validate_with_missing_fields(self):
        # Missing both phone_number and email
        serializer = GenerateOTPSerializer(data={"channel": "sms"})
        self.assertFalse(serializer.is_valid())

        # Missing country_iso_code when phone_number is provided
        serializer = GenerateOTPSerializer(data={"phone_number": "698765432"})
        self.assertFalse(serializer.is_valid())

    def test_validate_with_invalid_country(self):
        data = {
            "phone_number": "698765432",
            "country_iso_code": "XX",  # Invalid country code
            "channel": "sms",
        }
        serializer = GenerateOTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_channel_auto_switch_for_email(self):
        # When only email is provided but channel is sms, it should switch to email
        data = {
            "email": "test@example.com",
            "channel": "sms",
        }
        serializer = GenerateOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["channel"], "email")


class VerifyOTPSerializerTestCase(TestCase):
    def setUp(self):
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

    def test_validate_with_phone_number(self):
        serializer = VerifyOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["identifier"], "+237698765432")

    def test_validate_with_email(self):
        serializer = VerifyOTPSerializer(data=self.valid_email_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["identifier"], "test@example.com")

    def test_validate_with_missing_fields(self):
        # Missing both phone_number and email
        serializer = VerifyOTPSerializer(data={"code": "123456"})
        self.assertFalse(serializer.is_valid())

        # Missing country_iso_code when phone_number is provided
        serializer = VerifyOTPSerializer(
            data={"phone_number": "698765432", "code": "123456"}
        )
        self.assertFalse(serializer.is_valid())

        # Missing code
        serializer = VerifyOTPSerializer(
            data={"phone_number": "698765432", "country_iso_code": "CM"}
        )
        self.assertFalse(serializer.is_valid())

    def test_validate_with_invalid_country(self):
        data = {
            "phone_number": "698765432",
            "country_iso_code": "XX",  # Invalid country code
            "code": "123456",
        }
        serializer = VerifyOTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_validate_with_non_digit_code(self):
        data = {
            "phone_number": "698765432",
            "country_iso_code": "CM",
            "code": "12345A",  # Contains a non-digit character
        }
        serializer = VerifyOTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    @patch("app.verify.models.OTP.objects.get_active_otp")
    def test_verify_otp_no_active_otp(self, mock_get_active_otp):
        # Test when no active OTP is found
        mock_get_active_otp.return_value = None

        serializer = VerifyOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "No active OTP found. Please request a new code."
        )
        mock_get_active_otp.assert_called_once_with("+237698765432")

    @patch("app.verify.models.OTP.objects.get_active_otp")
    def test_verify_otp_invalid_code(self, mock_get_active_otp):
        # Test when the OTP code is invalid
        mock_otp = Mock()
        mock_otp.verify.return_value = False
        mock_otp.attempt_count = 1
        mock_get_active_otp.return_value = mock_otp

        serializer = VerifyOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Invalid code. 2 attempts remaining.")
        mock_get_active_otp.assert_called_once_with("+237698765432")
        mock_otp.verify.assert_called_once_with("123456")

    @patch("app.verify.models.OTP.objects.get_active_otp")
    def test_verify_otp_max_attempts_reached(self, mock_get_active_otp):
        # Test when maximum verification attempts are reached
        mock_otp = Mock()
        mock_otp.verify.return_value = False
        mock_otp.attempt_count = 3
        mock_get_active_otp.return_value = mock_otp

        serializer = VerifyOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"],
            "Maximum verification attempts reached. Please request a new code.",
        )
        mock_get_active_otp.assert_called_once_with("+237698765432")
        mock_otp.verify.assert_called_once_with("123456")

    @patch("app.verify.models.OTP.objects.get_active_otp")
    @patch("app.accounts.models.User.objects.get_or_create")
    @patch("rest_framework_simplejwt.tokens.RefreshToken.for_user")
    def test_verify_otp_successful_verification(
        self, mock_refresh_token, mock_get_or_create, mock_get_active_otp
    ):
        # Test successful OTP verification
        mock_otp = Mock()
        mock_otp.verify.return_value = True
        mock_get_active_otp.return_value = mock_otp

        # Create a mock user
        mock_user = Mock()
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.phone_number = "+237698765432"

        # Mock get_or_create to return a tuple (user, created)
        mock_get_or_create.return_value = (mock_user, False)

        # Create a mock token with a string representation
        mock_token = Mock()
        mock_token.access_token = "access_token_value"
        # Instead of trying to mock __str__, we'll use a custom class
        type(mock_token).__str__ = lambda self: "refresh_token_value"
        mock_refresh_token.return_value = mock_token

        serializer = VerifyOTPSerializer(data=self.valid_phone_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        self.assertEqual(result["user"]["full_name"], "Test User")
        self.assertEqual(result["user"]["email"], "test@example.com")
        self.assertEqual(result["user"]["phone_number"], "+237698765432")
        self.assertEqual(result["tokens"]["access"], "access_token_value")
        self.assertEqual(result["tokens"]["refresh"], "refresh_token_value")
        self.assertEqual(result["created"], False)

        mock_get_active_otp.assert_called_once_with("+237698765432")
        mock_otp.verify.assert_called_once_with("123456")
        mock_get_or_create.assert_called_once_with(email="+237698765432")
        mock_refresh_token.assert_called_once_with(mock_user)

    @patch("app.verify.models.OTP.objects.get_active_otp")
    @patch("app.accounts.models.User.objects.get_or_create")
    @patch("rest_framework_simplejwt.tokens.RefreshToken.for_user")
    @patch("app.accounts.models.AvailableCountry.objects.get")
    def test_verify_otp_sets_country(
        self,
        mock_country_get,
        mock_refresh_token,
        mock_get_or_create,
        mock_get_active_otp,
    ):
        # Test that country is set during OTP verification
        mock_otp = Mock()
        mock_otp.verify.return_value = True
        mock_get_active_otp.return_value = mock_otp

        # Create a mock user
        mock_user = Mock()
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.phone_number = "+237698765432"
        mock_user.country = None

        # Mock get_or_create to return a tuple (user, created)
        mock_get_or_create.return_value = (mock_user, False)

        # Create a mock country
        mock_country = Mock()
        mock_country.name = "Cameroon"
        mock_country_get.return_value = mock_country

        # Create a mock token with a string representation
        mock_token = Mock()
        mock_token.access_token = "access_token_value"
        type(mock_token).__str__ = lambda self: "refresh_token_value"
        mock_refresh_token.return_value = mock_token

        # Add country_iso_code to the valid data
        data = self.valid_phone_data.copy()
        data["country_iso_code"] = "CM"

        serializer = VerifyOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        # Check that the country was set on the user
        mock_country_get.assert_called_with(iso_code="CM")
        self.assertEqual(mock_user.country, mock_country)
        mock_user.save.assert_called_once()

        # Check that the country is included in the response
        self.assertEqual(result["user"]["country"], "Cameroon")

    @patch("app.verify.models.OTP.objects.get_active_otp")
    @patch("app.accounts.models.User.objects.get_or_create")
    @patch("rest_framework_simplejwt.tokens.RefreshToken.for_user")
    def test_verify_otp_with_email(
        self, mock_refresh_token, mock_get_or_create, mock_get_active_otp
    ):
        # Test OTP verification with email
        mock_otp = Mock()
        mock_otp.verify.return_value = True
        mock_get_active_otp.return_value = mock_otp

        # Create a mock user
        mock_user = Mock()
        mock_user.full_name = "Email User"
        mock_user.email = "test@example.com"
        mock_user.phone_number = None

        # Mock get_or_create to return a tuple (user, created)
        mock_get_or_create.return_value = (
            mock_user,
            True,
        )  # True indicates a new user was created

        # Create a mock token with a string representation
        mock_token = Mock()
        mock_token.access_token = "email_access_token"
        # Instead of trying to mock __str__, we'll use a custom class
        type(mock_token).__str__ = lambda self: "email_refresh_token"
        mock_refresh_token.return_value = mock_token

        serializer = VerifyOTPSerializer(data=self.valid_email_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.verify_otp()

        self.assertEqual(result["user"]["full_name"], "Email User")
        self.assertEqual(result["user"]["email"], "test@example.com")
        self.assertEqual(result["user"]["phone_number"], None)
        self.assertEqual(result["tokens"]["access"], "email_access_token")
        self.assertEqual(result["tokens"]["refresh"], "email_refresh_token")
        self.assertEqual(result["created"], True)

        mock_get_active_otp.assert_called_once_with("test@example.com")
        mock_otp.verify.assert_called_once_with("123456")
        mock_get_or_create.assert_called_once_with(email="test@example.com")
        mock_refresh_token.assert_called_once_with(mock_user)
