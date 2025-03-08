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
