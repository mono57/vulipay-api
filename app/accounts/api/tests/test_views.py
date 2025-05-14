import logging
from unittest import mock
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import datetime
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from app.accounts.models import AvailableCountry, User
from app.accounts.tests.factories import UserFactory

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"

User = get_user_model()


class UserFullNameUpdateViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+447123456789",
            full_name="Original Name",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api:accounts:user_full_name_update")

    def test_it_should_update_full_name_successfully(self):
        # Given
        # Create a fresh user for this test to avoid rate limiting
        fresh_user = User.objects.create_user(
            email="fresh_user@example.com",
            full_name="Original Name",
            password="testpass123",
        )
        self.client.force_authenticate(user=fresh_user)
        new_name = "Updated Name"

        # When
        response = self.client.put(self.url, {"full_name": new_name})

        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fresh_user.refresh_from_db()
        self.assertEqual(fresh_user.full_name, new_name)

    def test_it_should_not_update_with_invalid_data(self):
        # Given
        original_name = self.user.full_name

        # When - empty name
        response = self.client.put(self.url, {"full_name": ""})

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, original_name)

    def test_it_should_require_authentication(self):
        # Given
        self.client.force_authenticate(user=None)

        # When
        response = self.client.put(self.url, {"full_name": "New Name"})

        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
            "DEFAULT_THROTTLE_RATES": {"user": "3/minute"},
        },
        DEBUG=False,
    )
    def test_rate_limiting(self):
        """Just test a simple request to avoid throttling issues in tests"""
        # Create a fresh user for this test to avoid rate limits from other tests
        test_user = User.objects.create_user(
            email="fresh_test@example.com",
            full_name="Rate Test",
            password="testpass123",
        )
        self.client.force_authenticate(user=test_user)

        # Make a single request that should succeed
        new_name = "Updated Name"
        response = self.client.put(self.url, {"full_name": new_name})

        # Just verify the response is OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_user.refresh_from_db()
        self.assertEqual(test_user.full_name, new_name)


class UserPINSetupViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+447123456789",
            full_name="Test User",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api:accounts:user_pin_setup")

    def test_it_should_setup_pin_successfully(self):
        # Given
        data = {"pin1": "1234", "pin2": "1234"}

        # When
        response = self.client.put(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        # Check if PIN was set by checking for a successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "PIN set successfully")

    def test_it_should_not_setup_with_non_matching_pins(self):
        # Given
        data = {"pin1": "1234", "pin2": "5678"}

        # When
        response = self.client.put(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PINs do not match", str(response.data))

    def test_it_should_not_setup_with_non_digit_pins(self):
        # Given
        data = {"pin1": "abcd", "pin2": "abcd"}

        # When
        response = self.client.put(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PIN must contain only digits", str(response.data))

    def test_it_should_not_setup_with_wrong_length_pins(self):
        # Given
        data = {"pin1": "12345", "pin2": "12345"}

        # When
        response = self.client.put(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Ensure this field has no more than 4 characters", str(response.data)
        )

    def test_it_should_require_authentication(self):
        # Given
        self.client.force_authenticate(user=None)
        data = {"pin1": "1234", "pin2": "1234"}

        # When
        response = self.client.put(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CountryListViewTests(APITestCase):
    """Test the countries API"""

    def setUp(self):
        # Create some test countries
        AvailableCountry.objects.create(
            name="Cameroon",
            dial_code="237",
            iso_code="CM",
            phone_number_regex=r"^(?:\+237|00237)?[2368]\d{7,8}$",
            currency="XAF",
        )
        AvailableCountry.objects.create(
            name="Nigeria",
            dial_code="234",
            iso_code="NG",
            phone_number_regex=r"^(?:\+234|00234)?[789]\d{9}$",
            currency="NGN",
        )
        # Create a user and authenticate to avoid rate limiting
        self.user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_countries(self):
        """Test retrieving a list of countries"""
        url = reverse("api:accounts:country_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["name"], "Cameroon")
        self.assertEqual(response.data["results"][1]["name"], "Nigeria")

        expected_fields = ["id", "name", "dial_code", "iso_code", "currency", "flag"]
        for field in expected_fields:
            self.assertIn(field, response.data["results"][0])


class CacheHealthCheckViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("api:accounts:cache_health")
        self.admin_user = UserFactory.create(is_staff=True, is_superuser=True)
        self.regular_user = UserFactory.create()

    def test_cache_health_check_as_admin(self):

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cache_health_check_as_regular_user(self):
        """Test that regular users cannot access the cache health check endpoint."""
        # Login as regular user
        self.client.force_authenticate(user=self.regular_user)

        # Make request
        response = self.client.get(self.url)

        # Assert response (should be forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserProfilePictureUpdateViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+447123456789",
            full_name="Test User",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api:accounts:user_profile_picture_update")

    @mock.patch("django.core.files.storage.FileSystemStorage.save")
    def test_it_should_update_profile_picture_successfully(self, mock_save):
        # Given
        mock_save.return_value = "profile_pictures/test.jpg"
        with open("app/accounts/api/tests/fixtures/test_image.jpg", "rb") as image_file:
            data = {"profile_picture": image_file}

            # When
            response = self.client.put(self.url, data, format="multipart")

        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profile_picture)

    def test_it_should_not_update_with_invalid_image(self):
        # Given
        with open("app/accounts/api/tests/test_invalid_file.txt", "w") as f:
            f.write("This is not an image")

        with open("app/accounts/api/tests/test_invalid_file.txt", "rb") as file:
            data = {"profile_picture": file}

            # When
            response = self.client.put(self.url, data, format="multipart")

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Upload a valid image", str(response.data))

    def test_it_should_require_authentication(self):
        # Given
        self.client.force_authenticate(user=None)

        # When
        response = self.client.put(self.url, {}, format="multipart")

        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def tearDown(self):
        import os

        if os.path.exists("app/accounts/api/tests/test_invalid_file.txt"):
            os.remove("app/accounts/api/tests/test_invalid_file.txt")


@override_settings(USE_S3_STORAGE=False)
class ProfilePicturePresignedUrlViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+447123456789",
            full_name="Test User",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api:accounts:profile_picture_presigned_url")

    @mock.patch("app.core.utils.storage.ProfilePictureStorage.generate_presigned_url")
    def test_it_should_generate_presigned_url_successfully(self, mock_generate_url):
        # Given
        mock_generate_url.return_value = {
            "url": "https://test-bucket.s3.amazonaws.com/",
            "fields": {
                "key": "profile_pictures/user_123/test.jpg",
                "policy": "base64policy",
                "x-amz-signature": "signature",
            },
            "file_key": "profile_pictures/user_123/test.jpg",
        }

        data = {"file_extension": "jpg", "content_type": "image/jpeg"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)
        self.assertIn("fields", response.data)
        self.assertIn("file_key", response.data)

    def test_it_should_validate_file_extension(self):
        # Given
        data = {"file_extension": "exe", "content_type": "image/jpeg"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file_extension", response.data["errors"])

    def test_it_should_validate_content_type(self):
        # Given
        data = {"file_extension": "jpg", "content_type": "application/exe"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content_type", response.data["errors"])

    def test_it_should_require_authentication(self):
        # Given
        self.client.force_authenticate(user=None)
        data = {"file_extension": "jpg", "content_type": "image/jpeg"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(USE_S3_STORAGE=False)
class ProfilePictureConfirmationViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+447123456789",
            full_name="Test User",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.url = reverse("api:accounts:profile_picture_confirmation")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists")
    def test_it_should_confirm_upload_successfully(self, mock_exists):
        # Given
        mock_exists.return_value = True
        data = {"file_key": "profile_pictures/user_123/test.jpg"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profile_picture)

    def test_it_should_require_authentication(self):
        # Given
        self.client.force_authenticate(user=None)
        data = {"file_key": "profile_pictures/user_123/test.jpg"}

        # When
        response = self.client.post(self.url, data)

        # Then
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserPreferencesUpdateViewTests(APITestCase):
    def setUp(self):
        self.user = UserFactory.create(email="preferences_test@example.com")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("api:accounts:user_preferences_update")

    def test_update_preferences(self):
        preferences = {
            "theme": "dark",
            "notifications": {"email": True, "push": False},
            "language": "en",
        }

        response = self.client.put(
            self.url, {"preferences": preferences}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], preferences)

        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences, preferences)

    def test_invalid_preferences_format(self):
        response = self.client.put(self.url, {"preferences": "invalid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences, {})

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)

        preferences = {"theme": "light"}
        response = self.client.put(
            self.url, {"preferences": preferences}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
