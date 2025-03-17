from django.contrib.auth import get_user_model
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.test import APITestCase, URLPatternsTestCase
from rest_framework.views import APIView

from app.accounts.api.mixins import ValidPINRequiredMixin
from app.accounts.models import AvailableCountry
from app.accounts.tests.factories import AvailableCountryFactory, UserFactory

User = get_user_model()


class TestAPIView(ValidPINRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        # If we reach this point, the mixin has approved the request
        return Response({"success": True})


class ValidPINRequiredMixinTestCase(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("test-pin-endpoint/", TestAPIView.as_view(), name="test_pin_endpoint"),
    ]

    def setUp(self):
        super().setUp()

        self.country = AvailableCountryFactory(
            name="Test Country", dial_code="123", iso_code="TC", currency="USD"
        )

        self.user = UserFactory(email="testpin@example.com", country=self.country)
        self.user.set_pin("1234")
        self.user.save()

        self.url = reverse("test_pin_endpoint")

    def test_valid_pin_passes(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"pin": "1234"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"success": True})

    def test_missing_pin_raises_validation_error(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_pin_raises_permission_denied(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"pin": "5678"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ValidPINRequiredMixinIntegrationTestCase(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("test-pin-endpoint/", TestAPIView.as_view(), name="test_pin_endpoint"),
    ]

    def setUp(self):
        super().setUp()

        self.country = AvailableCountryFactory(
            name="Integration Test Country",
            dial_code="456",
            iso_code="IT",
            currency="EUR",
        )

        self.user = UserFactory(
            email="testpinintegration@example.com", country=self.country
        )
        self.user.set_pin("1234")
        self.user.save()

        self.url = reverse("test_pin_endpoint")

    def test_pin_check_with_jwt_auth(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(self.user).access_token

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        response = self.client.post(self.url, {"pin": "1234"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"success": True})

        response = self.client.post(self.url, {"pin": "9999"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
