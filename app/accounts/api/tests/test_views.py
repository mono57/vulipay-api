import datetime
from unittest.mock import patch

from django.utils import timezone
from django.conf import settings

from rest_framework import status

from app.accounts.models import AvailableCountry, PassCode, PhoneNumber
from app.core.utils import APIViewTestCase

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"

class PassCodeCreateAPIViewTestCase(APIViewTestCase):
    view_name = 'api:accounts_passcodes'

    def setUp(self):
        super().setUp()
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

    def test_it_should_not_create_code_until_waiting_time(self):
        with patch(twilio_send_message_path) as mocked_send_message:
            self.view_post(data=self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch(twilio_send_message_path) as mocked_send_message:
            response = self.view_post(data=self.registration_payload)
            data = response.data
            mocked_send_message.assert_not_called()
            self.assertIn("waiting_time", data)
            self.assertTrue(data.get("waiting_time") is not None)


    def test_it_should_increase_waiting_time_before_send_new_code(self):
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


class VerifyPassCodeAPIViewTestCase(APIViewTestCase):
    view_name = 'api:accounts_passcodes_verify'

    def setUp(self):
        super().setUp()
        self.country_payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "phone_number_regex": "^6[5-9][0-9]{7}$",
            "iso_code": "CM",
        }

        self.verify_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "code": 234353,
        }

        self.passcode_payload = {
            'phone_number': '698049742',
            'code': 234353,
            'country_iso_code': 'CM',
            'sent_date': datetime.datetime.now(timezone.utc)
        }

        PassCode.objects.create(**self.passcode_payload)
        AvailableCountry.objects.create(**self.country_payload)

    def test_it_should_verify_code(self):
        response = self.view_post(data=self.verify_payload)

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIsNotNone(data.get('access'))
        self.assertIsNotNone(data.get('refresh'))

    def test_it_should_not_verify_same_code_twice(self):
        response1 = self.view_post(data=self.verify_payload)
        response2 = self.view_post(data=self.verify_payload)

        self.assertTrue(response1.status_code == status.HTTP_201_CREATED)
        self.assertTrue(response2.status_code == status.HTTP_400_BAD_REQUEST)

    # def test_should_not_create_user_with_same_phone_number_twice(self):
    #     code1 = 234353

    #     confirmation_payload1 = {
    #         "phone_number": "698049742",
    #         "country_iso_code": "CM",
    #         "code": code1,
    #     }

    #     code2 = 234351

    #     confirmation_payload2 = {
    #         "phone_number": "698049742",
    #         "country_iso_code": "CM",
    #         "code": code2,
    #     }

    #     PassCodeFactory(
    #         code=code1, phone_number="+237698049742", sent=datetime.now(timezone.utc)
    #     )
    #     PassCodeFactory(
    #         code=code2, phone_number="+237698049742", sent=datetime.now(timezone.utc)
    #     )

    #     response1 = self.client.post(CONFIRM_CODE_URL, confirmation_payload1)

    #     self.assertTrue(response1.status_code == status.HTTP_200_OK)
    #     self.assertTrue(
    #         User.objects.filter(
    #             phone_number=confirmation_payload1.get("phone_number")
    #         ).count()
    #         == 1
    #     )

    #     response2 = self.client.post(CONFIRM_CODE_URL, confirmation_payload2)

    #     self.assertTrue(response2.status_code == status.HTTP_200_OK)
    #     self.assertTrue(
    #         User.objects.filter(
    #             phone_number=confirmation_payload1.get("phone_number")
    #         ).count()
    #         == 1
    #     )