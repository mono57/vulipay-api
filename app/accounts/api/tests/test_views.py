from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

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
