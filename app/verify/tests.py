import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from app.verify.models import OTP


class OTPModelTestCase(TestCase):
    def setUp(self):
        self.identifier = "+237698765432"
        self.code = "123456"
        self.expires_at = timezone.now() + datetime.timedelta(minutes=10)

        self.otp = OTP.objects.create(
            identifier=self.identifier,
            code=self.code,
            channel="sms",
            expires_at=self.expires_at,
        )

    def test_str_representation(self):
        self.assertEqual(str(self.otp), f"OTP for {self.identifier} (sms)")

    def test_is_valid_property(self):
        # Valid OTP
        self.assertTrue(self.otp.is_valid)

        # Expired OTP
        self.otp.is_expired = True
        self.assertFalse(self.otp.is_valid)
        self.otp.is_expired = False

        # Used OTP
        self.otp.is_used = True
        self.assertFalse(self.otp.is_valid)
        self.otp.is_used = False

        # Expired time
        self.otp.expires_at = timezone.now() - datetime.timedelta(minutes=1)
        self.assertFalse(self.otp.is_valid)

    def test_verify_with_correct_code(self):
        self.assertTrue(self.otp.verify(self.code))
        self.assertTrue(self.otp.is_used)
        self.assertIsNotNone(self.otp.used_at)

    def test_verify_with_incorrect_code(self):
        self.assertFalse(self.otp.verify("654321"))
        self.assertFalse(self.otp.is_used)
        self.assertIsNone(self.otp.used_at)
        self.assertEqual(self.otp.attempt_count, 1)

    def test_verify_with_expired_otp(self):
        self.otp.is_expired = True
        self.assertFalse(self.otp.verify(self.code))
        self.assertFalse(self.otp.is_used)

    def test_verify_with_max_attempts(self):
        with patch("app.verify.models.getattr") as mock_getattr:
            mock_getattr.return_value = 3  # Set max attempts to 3

            # First attempt (incorrect)
            self.assertFalse(self.otp.verify("654321"))
            self.assertEqual(self.otp.attempt_count, 1)
            self.assertFalse(self.otp.is_expired)

            # Second attempt (incorrect)
            self.assertFalse(self.otp.verify("654321"))
            self.assertEqual(self.otp.attempt_count, 2)
            self.assertFalse(self.otp.is_expired)

            # Third attempt (incorrect)
            self.assertFalse(self.otp.verify("654321"))
            self.assertEqual(self.otp.attempt_count, 3)
            self.assertFalse(self.otp.is_expired)

            # Fourth attempt (exceeds max attempts)
            self.assertFalse(self.otp.verify("654321"))
            self.assertEqual(self.otp.attempt_count, 4)
            self.assertTrue(self.otp.is_expired)

    def test_mark_as_expired(self):
        self.assertFalse(self.otp.is_expired)
        self.otp.mark_as_expired()
        self.assertTrue(self.otp.is_expired)


class OTPManagerTestCase(TestCase):
    def setUp(self):
        self.identifier = "+237698765432"

        # Create an active OTP
        self.active_otp = OTP.objects.create(
            identifier=self.identifier,
            code="123456",
            channel="sms",
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
        )

        # Create an expired OTP
        self.expired_otp = OTP.objects.create(
            identifier=self.identifier,
            code="654321",
            channel="sms",
            is_expired=True,
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
        )

        # Create a used OTP
        self.used_otp = OTP.objects.create(
            identifier=self.identifier,
            code="987654",
            channel="sms",
            is_used=True,
            used_at=timezone.now(),
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
        )

    def test_get_active_otp(self):
        otp = OTP.objects.get_active_otp(self.identifier)
        self.assertEqual(otp, self.active_otp)

    def test_get_active_otp_with_no_active_otp(self):
        # Mark the active OTP as expired
        self.active_otp.is_expired = True
        self.active_otp.save()

        otp = OTP.objects.get_active_otp(self.identifier)
        self.assertIsNone(otp)

    @patch("app.verify.models.random.choices")
    def test_create_otp(self, mock_choices):
        # Mock the random code generation
        mock_choices.return_value = ["1", "2", "3", "4", "5", "6"]

        # Create a new OTP
        new_otp = OTP.objects.create_otp(self.identifier)

        # Check that the active OTP is now expired
        self.active_otp.refresh_from_db()
        self.assertTrue(self.active_otp.is_expired)

        # Check the new OTP
        self.assertEqual(new_otp.identifier, self.identifier)
        self.assertEqual(new_otp.code, "123456")
        self.assertEqual(new_otp.channel, "sms")
        self.assertFalse(new_otp.is_used)
        self.assertFalse(new_otp.is_expired)
        self.assertGreater(new_otp.expires_at, timezone.now())
