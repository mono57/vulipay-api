import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from accounts.api.serializers import ConfirmCodeSerializer
from accounts.models import AvailableCountry
from accounts.models import PhoneNumberConfirmationCode as Code
from accounts.tests.factories import AvailableCountryFactory, CodeFactory
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

CREATE_USER_URL = reverse("accounts:register")
RESEND_CONFIRM_CODE_URL = reverse("accounts:resend-code")
CONFIRM_CODE_URL = reverse("accounts:confirm_code")


class TestPublicUserApi(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.registration_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
        }

        self.country_payload = {
            "name": "Cameroun",
            "calling_code": "237",
            "phone_number_regex": "^6[5-9][0-9]{7}$",
            "iso_code": "CM",
        }

        AvailableCountry.objects.create(**self.country_payload)

    def test_country_available(self):
        country = AvailableCountry.objects.get(**self.country_payload)

        self.assertTrue(isinstance(country, AvailableCountry))

    def test_create_inactive_user(self):
        with patch(
            "app.utils.twilio_client.MessageClient.send_message"
        ) as mocked_send_message:
            response = self.client.post(CREATE_USER_URL, self.registration_payload)

            self.assertTrue(response.status_code == status.HTTP_201_CREATED)

            mocked_send_message.assert_called_once()

            response_dict: dict = json.loads(response.content)

            self.assertTrue(len(response_dict.keys()) == 4)
            self.assertTrue("waiting_time" in response_dict.keys())
            self.assertEqual(response_dict["waiting_time"], 30)

    def test_can_verify_code(self):
        confirmation_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "code": 234353,
        }

        key = 234353

        CodeFactory(
            key=key, phone_number="+237698049742", sent=datetime.now(timezone.utc)
        )

        response = self.client.post(CONFIRM_CODE_URL, confirmation_payload)

        self.assertTrue(response.status_code == status.HTTP_200_OK)

    def test_cannot_verify_same_code_twice(self):
        key = 234353

        confirmation_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "code": key,
        }

        CodeFactory(
            key=key, phone_number="+237698049742", sent=datetime.now(timezone.utc)
        )

        response1 = self.client.post(CONFIRM_CODE_URL, confirmation_payload)
        response2 = self.client.post(CONFIRM_CODE_URL, confirmation_payload)

        self.assertTrue(response1.status_code == status.HTTP_200_OK)
        self.assertTrue(response2.status_code == status.HTTP_400_BAD_REQUEST)

    def test_resend_user_confirmation_code(self):
        response = self.client.post(RESEND_CONFIRM_CODE_URL, self.registration_payload)
        self.assertTrue(response.status_code == status.HTTP_200_OK)

    def test_can_confirm_code(self):
        pass
