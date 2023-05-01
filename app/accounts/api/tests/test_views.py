from unittest.mock import patch

from django.utils import timezone
from django.urls import reverse
from rest_framework import status

from app.accounts.models import AvailableCountry, PassCode, Account
from app.core.utils import APIViewTestCase

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"

access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjgzMDY3MDIzLCJpYXQiOjE2ODI2MzUwMjMsImp0aSI6IjU3ZjJmN2QzYjVjODQzZjVhYWNkMTY1MDgwZWYxMTdjIiwidXNlciI6MX0.PPTFDF5CfyJcxw6QFfOMsek_kCpJDZukqkWrarujiBA"

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

            self.assertTrue(response.status_code == status.HTTP_201_CREATED)
            mocked_send_message.assert_called_once()

    def test_it_should_not_create_code_until_next_attempt_time_expired(self):
        with patch(twilio_send_message_path) as mocked_send_message:
            self.view_post(data=self.registration_payload)
            mocked_send_message.assert_called_once()

        with patch(twilio_send_message_path) as mocked_send_message:
            self.view_post(data=self.registration_payload)
            mocked_send_message.assert_not_called()


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
        time_now = timezone.now()
        self.passcode_payload = {
            'intl_phonenumber': '+237698049742',
            'code': 234353,
            'sent_on': time_now,
            'next_passcode_on': time_now,
            'next_verif_attempt_on': time_now,
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

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

class AccountPaymentCodeRetrieveAPIViewTestCase(APIViewTestCase):
    view_name = 'api:accounts_payment_code'

    def setUp(self):
        super().setUp()
        self.account: Account = Account.objects.create()
        self.account_number = self.account.number

    # def test_it_should_raise_unauthorize_error(self):
    #     response = self.view_get(reverse_kwargs={"number": self.account_number})

    #     self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_return_payment_code(self):
        response = self.view_get(reverse_kwargs={"number": self.account_number})

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payment_code', data)
        self.assertEqual(data.get('payment_code'), self.account.payment_code)


class AccountPaymentDetailsTestCase(APIViewTestCase):
    view_name = 'api:accounts_payment_details'

    def setUp(self):
        super().setUp()
        self.payment_code = '126543TDS23YTHGSFGHY34GHFDSD'

        self.account_payload = {
            'owner_first_name': 'Aymar',
            'owner_last_name': 'Amono',
        }
        with patch('app.accounts.models.Hasher.hash') as mocked_hash:
            mocked_hash.return_value = self.payment_code
            Account.objects.create(**self.account_payload)

    def test_it_should_raise_access_denied_error(self):
        response = self.view_get(reverse_kwargs={'payment_code': self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_it_should_retrieve_account_payment_details_information(self):
        # self.authenticate_with_access_token(access_token)
        reserve_url = reverse(self.view_name, kwargs={'payment_code': self.payment_code})
        authorization = 'Bearer ' + access_token
        response = self.client_class.get(reserve_url, HTTP_AUTHORIZATION=authorization)
        print('Response data', response.data)
        # response = self.view_get(reverse_kwargs={'payment_code': self.payment_code})
        # data = response.data
        # self.assertEqual(response.status_code, status.HTTP_200_OK)