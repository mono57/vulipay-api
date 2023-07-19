from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import Account, AvailableCountry, PassCode
from app.accounts.tests.factories import AccountFactory, AvailableCountryFactory
from app.core.utils import APIViewTestCase

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"

access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjgzNTc2ODI1LCJpYXQiOjE2ODMxNDQ4MjUsImp0aSI6IjAzY2MyMjlmYzlhMTQxOWRiZWI1ZGYxNTQwZDQzNzJmIiwiYWNjb3VudF9pZCI6Mn0.5DXBP_SHHfJjl25oVThAgXy1J7Hburjc7FYuAdsiSko"


class PassCodeCreateAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_passcodes"

    def setUp(self):
        super().setUp()
        self.registration_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
        }

        AvailableCountryFactory.create()

    def test_it_should_not_generate_passcode_for_empty_payload(self):
        response = self.view_post({})
        data = response.data

        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", data)
        self.assertIn("country_iso_code", data)

    def test_it_should_not_generate_passcode_for_unknown_country(self):
        response = self.view_post(
            {**self.registration_payload, "country_iso_code": "TD"}
        )

        data = response.data

        self.assertTrue(response.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertIn("country_iso_code", data)

    def test_it_should_not_generate_passcode_for_invalid_number(self):
        response = self.view_post(
            {**self.registration_payload, "phone_number": "000000000000"}
        )

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
    view_name = "api:accounts:accounts_passcodes_verify"

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
            "intl_phone_number": "+237698049742",
            "code": 234353,
            "sent_on": time_now,
            "next_passcode_on": time_now,
            "next_verif_attempt_on": time_now,
        }
        PassCode.objects.create(**self.passcode_payload)
        AvailableCountry.objects.create(**self.country_payload)

    def test_it_should_verify_code(self):
        response = self.view_post(data=self.verify_payload)

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIsNotNone(data.get("access"))
        self.assertIsNotNone(data.get("refresh"))

    def test_it_should_not_verify_same_code_twice(self):
        response1 = self.view_post(data=self.verify_payload)
        response2 = self.view_post(data=self.verify_payload)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)


class AccountPaymentCodeRetrieveAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_payment_code"

    def setUp(self):
        super().setUp()
        self.account: Account = AccountFactory.create()
        self.account_number = self.account.number
        self.access_token = str(RefreshToken.for_user(self.account).access_token)

    def test_it_should_raise_unauthorize_error(self):
        response = self.view_get(reverse_kwargs={"number": self.account_number})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_return_payment_code(self):
        self.authenticate_with_jwttoken(self.access_token)
        response = self.view_get(reverse_kwargs={"number": self.account_number})

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_code", data)
        self.assertEqual(data.get("payment_code"), self.account.payment_code)


class AccountPaymentDetailsTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_payment_details"

    def setUp(self):
        super().setUp()
        self.payment_code = "126543TDS23YTHGSFGHY34GHFDSD"

        self.account_payload = {
            "owner_first_name": "Aymar",
            "owner_last_name": "Amono",
        }
        with patch("app.accounts.models.make_payment_code") as mocked_make_payment_code:
            mocked_make_payment_code.return_value = self.payment_code
            account = AccountFactory.create(**self.account_payload)
            self.access_token = str(RefreshToken.for_user(account).access_token)

    def test_it_should_raise_access_denied_error(self):
        response = self.view_get(reverse_kwargs={"payment_code": self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_retrieve_account_payment_details_information(self):
        self.authenticate_with_jwttoken(self.access_token)
        response = self.view_get(reverse_kwargs={"payment_code": self.payment_code})

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("number", data)
        self.assertIn("first_name", data)
        self.assertIn("last_name", data)
        self.assertEqual(self.account_payload.get("owner_last_name"), data["last_name"])
        self.assertEqual(
            self.account_payload.get("owner_first_name"), data["first_name"]
        )


class PinCreationUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_set_pin"

    def setUp(self):
        super().setUp()

        self.account = AccountFactory.create()
        self.access_token = str(RefreshToken.for_user(self.account).access_token)

        self.payload = {
            "pin1": "3549",
            "pin2": "3549",
        }

    def test_it_should_set_account_pin(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_put(data=self.payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_it_should_raise_access_denied_error(self):
        response = self.view_put(data=self.payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AccountBalanceRetrieveAPIView(APIViewTestCase):
    view_name = "api:accounts:accounts_balance"

    def setUp(self):
        super().setUp()
        self.account_balance = float(5000)
        self.account: Account = AccountFactory.create(balance=self.account_balance)

    def test_it_should_retrieve_correct_balance(self):
        self.authenticate_with_account(self.account)

        response = self.view_get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data)
