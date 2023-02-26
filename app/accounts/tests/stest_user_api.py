import datetime
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.tests.factories import AvailableCountryFactory
from accounts.models import AvailableCountry

User = get_user_model()


class TestPublicUserApi(TestCase):
    GENERATE_CODE_URL = reverse("api:users:generate_code")

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

    def test_should_create_new_code(self):
        with patch(
            "app.utils.twilio_client.MessageClient.send_message"
        ) as mocked_send_message:
            response = self.client.post(
                self.GENERATE_CODE_URL, self.registration_payload
            )

            self.assertTrue(response.status_code == status.HTTP_201_CREATED)

            mocked_send_message.assert_called_once()

            response_dict: dict = json.loads(response.content)

            self.assertTrue(len(response_dict.keys()) == 4)
            self.assertTrue("waiting_time" in response_dict.keys())
            self.assertEqual(response_dict["waiting_time"], 30)

    def test_should_not_create_code_until_waiting_time(self):
        with patch(
            "app.utils.twilio_client.MessageClient.send_message"
        ) as mocked_send_message:
            self.client.post(self.GENERATE_CODE_URL, self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch(
            "app.utils.twilio_client.MessageClient.send_message"
        ) as mocked_send_message:
            response = self.client.post(
                self.GENERATE_CODE_URL, self.registration_payload
            )

            self.assertTrue(response.status_code == status.HTTP_401_UNAUTHORIZED)

            mocked_send_message.assert_not_called()

    def test_should_increase_waiting_time_before_send_new_code(self):
        with patch(
            "app.utils.twilio_client.MessageClient.send_message"
        ) as mocked_send_message:
            self.client.post(self.GENERATE_CODE_URL, self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch("users.models.datetime") as mocked_datetime:
            mocked_datetime.datetime.now.return_value = datetime.datetime.now(
                timezone.utc
            ) + datetime.timedelta(seconds=30)

            with patch(
                "app.utils.twilio_client.MessageClient.send_message"
            ) as mocked_send_message:
                response = self.client.post(
                    self.GENERATE_CODE_URL, self.registration_payload
                )

                mocked_send_message.assert_called_once()

                self.assertTrue(response.status_code == status.HTTP_201_CREATED)

                response_dict: dict = json.loads(response.content)

                self.assertTrue(len(response_dict.keys()) == 4)
                self.assertTrue("waiting_time" in response_dict.keys())
                self.assertTrue(response_dict["waiting_time"] > 30)
