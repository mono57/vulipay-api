from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import Account, AvailableCountry
from app.accounts.tests.factories import (
    AccountFactory,
    AvailableCountryFactory,
    CarrierFactory,
    PhoneNumberFactory,
)
from app.core.utils import APIViewTestCase

twilio_send_message_path = "app.core.utils.twilio_client.MessageClient.send_message"


class AccountPaymentCodeRetrieveAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_payment_code"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.token = RefreshToken.for_user(self.account).access_token

    def test_it_should_raise_unauthorize_error(self):
        response = self.view_get({"number": self.account.number})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_return_payment_code(self):
        response = self.view_get({"number": self.account.number}, token=str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_code", response.data)
        self.assertEqual(response.data["payment_code"], self.account.payment_code)


class AccountPaymentDetailsTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_payment_details"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create(
            owner_first_name="John", owner_last_name="Doe"
        )
        self.token = RefreshToken.for_user(self.account).access_token

        self.url_kwargs = {"payment_code": self.account.payment_code}

    def test_it_should_raise_access_denied_error(self):
        response = self.view_get(self.url_kwargs)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_retrieve_account_payment_details_information(self):
        response = self.view_get(self.url_kwargs, token=str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("number", response.data)
        self.assertIn("first_name", response.data)
        self.assertIn("last_name", response.data)

        self.assertEqual(response.data["number"], self.account.number)
        self.assertEqual(response.data["first_name"], self.account.owner_first_name)
        self.assertEqual(response.data["last_name"], self.account.owner_last_name)


class PinCreationUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_set_pin"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.token = RefreshToken.for_user(self.account).access_token

        self.url_kwargs = {"number": self.account.number}
        self.payload = {"pin1": "2343", "pin2": "2343"}

    def test_it_should_set_account_pin(self):
        response = self.view_put(self.url_kwargs, self.payload, token=str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_it_should_raise_access_denied_error(self):
        response = self.view_put(self.url_kwargs, self.payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AccountBalanceRetrieveAPIView(APIViewTestCase):
    view_name = "api:accounts:accounts_balance"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create(balance=5000)
        self.token = RefreshToken.for_user(self.account).access_token

    def test_it_should_retrieve_correct_balance(self):
        response = self.view_get({"number": self.account.number}, token=str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("balance", response.data)
        self.assertEqual(response.data["balance"], self.account.balance)


class ModifyPINUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_modify_pin"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.token = RefreshToken.for_user(self.account).access_token

    def test_it_should_modify_pin_successfully(self):
        self.account.set_pin("2343")
        self.account.save()

        payload = {"pin": "2343", "pin1": "2344", "pin2": "2344"}
        response = self.view_put(
            {"number": self.account.number}, payload, token=str(self.token)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class VerifyPhoneNumberListAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_phonenumbers_list_create"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.token = RefreshToken.for_user(self.account).access_token

    def test_it_should_list_account_related_phonenumbers(self):
        PhoneNumberFactory.create(account=self.account)
        response = self.view_get({}, token=str(self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class AccountInfoUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:accounts:accounts_update_infos"

    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.token = RefreshToken.for_user(self.account).access_token

    def test_it_should_modify_account_info_successfully(self):
        payload = {"first_name": "John", "last_name": "Doe"}
        response = self.view_put(
            {"number": self.account.number}, payload, token=str(self.token)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.account.refresh_from_db()
        self.assertEqual(self.account.owner_first_name, payload["first_name"])
        self.assertEqual(self.account.owner_last_name, payload["last_name"])

    def test_it_should_raise_invalid_data(self):
        payload = {"first_name": "", "last_name": ""}
        response = self.view_put(
            {"number": self.account.number}, payload, token=str(self.token)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
