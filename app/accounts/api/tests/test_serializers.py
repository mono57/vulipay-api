from django.contrib.auth import get_user_model
from django.test import TestCase

from app.accounts.api.serializers import (
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
)

User = get_user_model()


class UserFullNameUpdateSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test_serializer@example.com",
            password="testpassword123",
            full_name="Original Name",
        )

        self.serializer_data = {"full_name": "Updated Full Name"}

        self.serializer = UserFullNameUpdateSerializer(
            instance=self.user, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_empty_full_name(self):
        """Test that the serializer rejects empty full_name"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_whitespace_full_name(self):
        """Test that the serializer rejects full_name with only whitespace"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": "   "}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_update_user(self):
        self.serializer.is_valid()
        self.serializer.save()

        updated_user = User.objects.get(pk=self.user.pk)
        self.assertEqual(updated_user.full_name, self.serializer_data["full_name"])

    def test_serializer_output(self):
        """Test that the serializer output contains the correct fields"""
        serializer = UserFullNameUpdateSerializer(instance=self.user)
        data = serializer.data

        self.assertIn("full_name", data)
        self.assertEqual(data["full_name"], self.user.full_name)


class UserPINSetupSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test_pin_serializer@example.com",
            full_name="PIN Test User",
        )

        self.serializer_data = {"pin1": "1234", "pin2": "1234"}

        self.serializer = UserPINSetupSerializer(
            instance=self.user, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_non_digit_pin(self):
        """Test that the serializer rejects non-digit PIN"""
        serializer = UserPINSetupSerializer(
            instance=self.user, data={"pin1": "123a", "pin2": "123a"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("pin1", serializer.errors)

    def test_serializer_wrong_length_pin(self):
        """Test that the serializer rejects PIN with wrong length"""
        # Too short
        serializer_short = UserPINSetupSerializer(
            instance=self.user, data={"pin1": "123", "pin2": "123"}
        )
        self.assertFalse(serializer_short.is_valid())
        self.assertIn("pin1", serializer_short.errors)

        # Too long
        serializer_long = UserPINSetupSerializer(
            instance=self.user, data={"pin1": "12345", "pin2": "12345"}
        )
        self.assertFalse(serializer_long.is_valid())
        self.assertIn("pin1", serializer_long.errors)

    def test_serializer_pins_dont_match(self):
        """Test that the serializer rejects when PINs don't match"""
        serializer = UserPINSetupSerializer(
            instance=self.user, data={"pin1": "1234", "pin2": "5678"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_serializer_update_user(self):
        self.serializer.is_valid()
        self.serializer.save()

        updated_user = User.objects.get(pk=self.user.pk)
        self.assertIsNotNone(updated_user.pin)
        self.assertTrue(updated_user.verify_pin(self.serializer_data["pin1"]))
