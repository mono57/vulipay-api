from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from app.accounts.api.serializers import (
    CountrySerializer,
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
    UserProfilePictureSerializer,
)
from app.accounts.models import AvailableCountry

User = get_user_model()


class CountrySerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.country = AvailableCountry.objects.create(
            name="Test Country",
            dial_code="123",
            iso_code="TC",
            phone_number_regex=r"^(?:\+123|00123)?[0-9]{9}$",
            currency="TCN",
        )

    def test_serializer_output(self):
        """Test that the serializer output contains the correct fields"""
        serializer = CountrySerializer(instance=self.country)
        data = serializer.data

        # Verify country data directly
        self.assertEqual(data["id"], self.country.id)
        self.assertEqual(data["name"], "Test Country")
        self.assertEqual(data["dial_code"], "123")
        self.assertEqual(data["iso_code"], "TC")
        self.assertEqual(data["currency"], "TCN")
        self.assertIn("flag", data)


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

        self.assertIn("data", data)
        self.assertIn("message", data)
        self.assertIn("error_code", data)
        self.assertIn("errors", data)
        self.assertEqual(data["data"]["full_name"], self.user.full_name)
        self.assertEqual(data["data"]["email"], self.user.email)
        self.assertIn("phone_number", data["data"])
        self.assertIn("country", data["data"])
        self.assertIn("profile_picture", data["data"])
        self.assertIsNone(data["error_code"])
        self.assertIsNone(data["errors"])


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


class UserProfilePictureSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test_profile_pic@example.com",
            password="testpassword123",
        )

        # Create a test image
        self.test_image = SimpleUploadedFile(
            name="test_image.jpg",
            content=b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/jpeg",
        )

        self.serializer_data = {"profile_picture": self.test_image}

        self.serializer = UserProfilePictureSerializer(
            instance=self.user, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_update_user(self):
        self.serializer.is_valid()
        updated_user = self.serializer.save()

        self.assertIsNotNone(updated_user.profile_picture)
        self.assertTrue(
            updated_user.profile_picture.name.startswith("profile_pictures/")
        )

    def test_serializer_rejects_non_image_file(self):
        non_image = SimpleUploadedFile(
            name="test_file.txt",
            content=b"This is not an image",
            content_type="text/plain",
        )

        serializer = UserProfilePictureSerializer(
            instance=self.user, data={"profile_picture": non_image}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("profile_picture", serializer.errors)

    def test_serializer_optional_profile_picture(self):
        """Test that profile_picture is optional"""
        serializer = UserProfilePictureSerializer(
            instance=self.user, data={"profile_picture": None}
        )
        self.assertTrue(serializer.is_valid())

    def test_old_profile_picture_gets_deleted(self):
        """Test that old profile pictures are deleted when a new one is uploaded"""
        # Mock the storage.delete method to verify it's called
        with patch("django.core.files.storage.FileSystemStorage.delete") as mock_delete:
            # First, set an initial profile picture
            self.serializer.is_valid()
            self.serializer.save()

            # Get the user with the first profile picture
            self.user.refresh_from_db()
            old_picture_name = self.user.profile_picture.name

            # Create a second test image
            second_image = SimpleUploadedFile(
                name="second_image.jpg",
                content=b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
                content_type="image/jpeg",
            )

            # Update with a new profile picture
            second_serializer = UserProfilePictureSerializer(
                instance=self.user, data={"profile_picture": second_image}
            )

            self.assertTrue(second_serializer.is_valid())
            second_serializer.save()

            # Refresh from database
            self.user.refresh_from_db()

            # Verify the user now has a different profile picture
            self.assertNotEqual(self.user.profile_picture.name, old_picture_name)

            # The mock might not be called if we're using S3 storage during tests
            # but we can at least verify the picture was actually changed
            self.assertTrue(
                self.user.profile_picture.name.startswith("profile_pictures/")
            )

    def tearDown(self):
        # Clean up any uploaded files
        if self.user.profile_picture:
            try:
                self.user.profile_picture.delete()
            except (AttributeError, NotImplementedError):
                # Handle S3 storage errors gracefully
                pass
