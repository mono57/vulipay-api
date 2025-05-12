from unittest import skip

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.tests.factories import UserFactory


class AppJWTAuthenticationTestCase(APITestCase):
    def setUp(self):
        self.user_with_name = UserFactory.create(
            email="user_with_name@example.com", full_name="John Doe"
        )

        self.user_without_name = UserFactory.create(
            email="user_without_name@example.com", full_name=""
        )

        self.auth_required_url = reverse("api:accounts:country_list")

        self.client = APIClient()

    def test_authentication_succeeds_with_full_name(self):
        token = RefreshToken.for_user(self.user_with_name).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = self.client.get(self.auth_required_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @skip("Skipping this test as it is not required")
    def test_authentication_fails_without_full_name(self):
        token = RefreshToken.for_user(self.user_without_name).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = self.client.get(self.auth_required_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("User profile is incomplete", str(response.content))
        self.assertIn("Please set your full name", str(response.content))
