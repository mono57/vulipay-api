from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import AvailableCountry, User

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"

User = get_user_model()


class UserFullNameUpdateViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            full_name="Original Name",
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.url = reverse("api:accounts:user_full_name_update")

    def test_it_should_update_full_name_successfully(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"full_name": "New Full Name"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, payload["full_name"])

    def test_it_should_require_authentication(self):
        payload = {"full_name": "New Full Name"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_reject_empty_full_name(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"full_name": ""}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Original Name")


class UserPINSetupViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            full_name="Test User",
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.url = reverse("api:accounts:user_pin_setup")

    def test_it_should_set_pin_successfully(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"pin1": "1234", "pin2": "1234"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "PIN set successfully")

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.pin)
        self.assertTrue(self.user.verify_pin("1234"))

    def test_it_should_require_authentication(self):
        payload = {"pin1": "1234", "pin2": "1234"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_reject_non_digit_pin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"pin1": "123a", "pin2": "123a"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pin1", response.data)

    def test_it_should_reject_wrong_length_pin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"pin1": "12345", "pin2": "12345"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pin1", response.data)

    def test_it_should_reject_mismatched_pins(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")
        payload = {"pin1": "1234", "pin2": "5678"}
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)


class CountryListViewTests(TestCase):
    """Test the countries API"""

    def setUp(self):
        self.client = APIClient()
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

    def test_list_countries(self):
        """Test retrieving a list of countries"""
        url = reverse("api:accounts:country_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Cameroon")
        self.assertEqual(response.data[1]["name"], "Nigeria")

        # Check that all expected fields are present
        expected_fields = ["id", "name", "dial_code", "iso_code", "currency"]
        for field in expected_fields:
            self.assertIn(field, response.data[0])
