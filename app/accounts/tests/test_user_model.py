import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase

from app.accounts.models import User
from app.accounts.tests.factories import AvailableCountryFactory, UserFactory


class UserModelTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()
        self.user_with_email = UserFactory.create(
            email="test@example.com", phone_number=None
        )
        self.user_with_phone = UserFactory.create(
            email=None, phone_number="+237698049700"
        )
        self.user_with_both = UserFactory.create(
            email="both@example.com", phone_number="+237698049701"
        )
        self.user = UserFactory.create()

    def test_user_creation_with_email_only(self):
        """Test that a user can be created with only an email"""
        self.assertIsNotNone(self.user_with_email)
        self.assertEqual(self.user_with_email.email, "test@example.com")
        self.assertIsNone(self.user_with_email.phone_number)

    def test_user_creation_with_phone_only(self):
        """Test that a user can be created with only a phone number"""
        self.assertIsNotNone(self.user_with_phone)
        self.assertEqual(self.user_with_phone.phone_number, "+237698049700")
        self.assertIsNone(self.user_with_phone.email)

    def test_user_creation_with_both_email_and_phone(self):
        """Test that a user can be created with both email and phone number"""
        self.assertIsNotNone(self.user_with_both)
        self.assertEqual(self.user_with_both.email, "both@example.com")
        self.assertEqual(self.user_with_both.phone_number, "+237698049701")

    def test_user_creation_fails_without_email_or_phone(self):
        """Test that a user cannot be created without either email or phone number"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, phone_number=None)

    def test_user_string_representation(self):
        """Test the string representation of users"""
        self.assertEqual(str(self.user_with_email), "test@example.com")
        self.assertEqual(str(self.user_with_phone), "+237698049700")
        self.assertEqual(
            str(self.user_with_both), "+237698049701"
        )  # Phone number takes precedence

        # Test with country
        self.user_with_email.country = self.country
        self.user_with_email.save()
        self.assertEqual(
            str(self.user_with_email), f"test@example.com ({self.country.name})"
        )

    def test_get_full_name(self):
        """Test the get_full_name method"""
        user = UserFactory.create(full_name="John Doe")
        self.assertEqual(user.get_full_name(), "John Doe")

        # Test with empty full_name
        user = UserFactory.create(full_name="")
        self.assertEqual(user.get_full_name(), "")

    def test_get_short_name(self):
        """Test the get_short_name method"""
        user = UserFactory.create(full_name="John Doe")
        self.assertEqual(user.get_short_name(), "John")

        # Test with empty full_name
        user = UserFactory.create(full_name="")
        self.assertEqual(user.get_short_name(), "")

    def test_email_uniqueness(self):
        """Test that email addresses must be unique"""
        with self.assertRaises(IntegrityError):
            UserFactory.create(email="test@example.com")

    def test_phone_number_uniqueness(self):
        """Test that phone numbers must be unique"""
        with self.assertRaises(IntegrityError):
            UserFactory.create(phone_number="+237698049700")

    def test_user_with_country(self):
        """Test that a user can have a country associated with it"""
        user = UserFactory.create(email="country@example.com")
        self.assertIsNone(user.country)

        user.country = self.country
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.country, self.country)
        self.assertEqual(user.country.name, self.country.name)
        self.assertEqual(user.country.iso_code, self.country.iso_code)

    def test_user_model_has_profile_picture(self):
        """Test that the User model has a profile_picture field"""
        self.assertTrue(hasattr(self.user, "profile_picture"))

    def test_profile_picture_is_optional(self):
        """Test that profile_picture is optional (can be null/blank)"""
        user = UserFactory.create(profile_picture=None)
        self.assertIsNone(user.profile_picture.name)

    def test_profile_picture_upload(self):
        """Test that a profile picture can be uploaded and retrieved"""
        # Create a temporary image file for testing
        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
            # Write some dummy data to the file
            temp_file.write(
                b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
            )
            temp_file.flush()

            # Create a SimpleUploadedFile from the temp file
            img = SimpleUploadedFile(
                name="test_upload.jpg",
                content=open(temp_file.name, "rb").read(),
                content_type="image/jpeg",
            )

            # Create a user with this profile picture
            user = UserFactory.create(profile_picture=img)

            # Check that the profile picture is saved and accessible
            self.assertIsNotNone(user.profile_picture)

            # Check the filename follows our expected format (profile_pictures/ directory and UUID-like name)
            file_path_parts = user.profile_picture.name.split("/")
            self.assertEqual(file_path_parts[0], "profile_pictures")

            # If we're using local storage, the file should exist on the filesystem
            from django.conf import settings

            if not getattr(settings, "USE_S3_STORAGE", False):
                try:
                    # Check if file exists on filesystem (only for local storage)
                    self.assertTrue(os.path.exists(user.profile_picture.path))

                    # Clean up the test file
                    if os.path.exists(user.profile_picture.path):
                        os.remove(user.profile_picture.path)
                except NotImplementedError:
                    # S3 storage doesn't support path, so we'll skip this check
                    pass

    def test_user_preferences(self):
        """Test that user preferences are stored and retrieved correctly"""
        # Test default empty preferences
        user = UserFactory.create()
        self.assertEqual(user.preferences, {})

        # Test setting preferences
        test_preferences = {
            "theme": "dark",
            "notifications": {"email": True, "push": False},
            "language": "en",
        }
        user.preferences = test_preferences
        user.save()

        # Refresh from database and verify
        user.refresh_from_db()
        self.assertEqual(user.preferences, test_preferences)
        self.assertEqual(user.preferences["theme"], "dark")
        self.assertEqual(user.preferences["notifications"]["email"], True)
        self.assertEqual(user.preferences["notifications"]["push"], False)
        self.assertEqual(user.preferences["language"], "en")
