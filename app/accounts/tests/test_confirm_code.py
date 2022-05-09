from datetime import datetime
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AvailableCountry
from accounts.tests.factories import CodeFactory

User = get_user_model()

CONFIRM_CODE_URL = reverse("api:accounts:confirm_code")


class ConfirmCodeTestCase(TestCase):
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

    def test_should_verify_code(self):
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

    def test_should_not_verify_same_code_twice(self):
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

        self.assertTrue(User.objects.count() == 1)
        self.assertTrue(response1.status_code == status.HTTP_200_OK)
        self.assertTrue(response2.status_code == status.HTTP_400_BAD_REQUEST)

    def test_should_not_create_user_with_same_phone_number_twice(self):
        key1 = 234353

        confirmation_payload1 = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "code": key1,
        }

        key2 = 234351

        confirmation_payload2 = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "code": key2,
        }

        CodeFactory(
            key=key1, phone_number="+237698049742", sent=datetime.now(timezone.utc)
        )
        CodeFactory(
            key=key2, phone_number="+237698049742", sent=datetime.now(timezone.utc)
        )

        response1 = self.client.post(CONFIRM_CODE_URL, confirmation_payload1)

        self.assertTrue(response1.status_code == status.HTTP_200_OK)
        self.assertTrue(
            User.objects.filter(
                phone_number=confirmation_payload1.get("phone_number")
            ).count()
            == 1
        )

        response2 = self.client.post(CONFIRM_CODE_URL, confirmation_payload2)

        self.assertTrue(response2.status_code == status.HTTP_200_OK)
        self.assertTrue(
            User.objects.filter(
                phone_number=confirmation_payload1.get("phone_number")
            ).count()
            == 1
        )
