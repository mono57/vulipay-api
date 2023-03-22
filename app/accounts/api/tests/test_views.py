import json, datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from rest_framework import status

from app.accounts.models import AvailableCountry
from app.utils.test_utils import APIViewTestCase

twilio_send_message_path = "app.utils.twilio_client.MessageClient.send_message"

class PassCodeCreateAPIViewTestCase(APIViewTestCase):
    view_name = 'api:accounts_passcodes'

    def setUp(self):
        self.registration_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
        }

        self.country_payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "REGEX"
        }

        AvailableCountry.objects.create(**self.country_payload)

        return super().setUp()

    def test_it_should_not_generate_passcode_for_empty_payload(self):
        response = self.view_post({})
        data = response.data

        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", data)
        self.assertIn("country_iso_code", data)

    def test_it_should_not_generate_passcode_for_unknown_country(self):
        response = self.view_post({ **self.registration_payload, "country_iso_code": "TD" })

        data = response.data

        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn("country_iso_code", data)

    def test_it_should_not_generate_passcode_for_invalid_number(self):
        response = self.view_post({ **self.registration_payload, "phone_number": "000000000000" })

        data = response.data

        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", data)

    def test_it_should_generate_and_send_passcode(self):
        with patch(twilio_send_message_path) as mocked_send_message:
            response = self.view_post(data=self.registration_payload)

            data = response.data

            self.assertTrue(response.status_code == status.HTTP_201_CREATED)
            mocked_send_message.assert_called_once()
            self.assertIn("waiting_time", data)
            self.assertTrue(data.get("waiting_time") is not None)
            self.assertEqual(round(data.get("waiting_time")), settings.DEFAULT_WAITING_TIME_SECONDS)

    def test_should_not_create_code_until_waiting_time(self):
        with patch(twilio_send_message_path) as mocked_send_message:
            self.view_post(data=self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch(twilio_send_message_path) as mocked_send_message:
            response = self.view_post(data=self.registration_payload)
            data = response.data
            mocked_send_message.assert_not_called()
            self.assertIn("waiting_time", data)
            self.assertTrue(data.get("waiting_time") is not None)


    def test_should_increase_waiting_time_before_send_new_code(self):
        with patch(twilio_send_message_path) as mocked_send_message:
            self.view_post(data=self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch("app.accounts.models.datetime") as mocked_datetime:
            mocked_datetime.datetime.now.return_value = datetime.datetime.now(timezone.utc) \
                + datetime.timedelta(seconds=30)

            with patch( twilio_send_message_path) as mocked_send_message:
                response = self.view_post(data=self.registration_payload)

                mocked_send_message.assert_called_once()

                self.assertTrue(response.status_code == status.HTTP_201_CREATED)

                data = response.data

                self.assertIn("waiting_time", data)
                self.assertTrue(data["waiting_time"] > 30)
                self.assertTrue(data.get("waiting_time") is not None)
