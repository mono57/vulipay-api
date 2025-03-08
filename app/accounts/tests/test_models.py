import datetime
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from app.accounts.models import (
    Account,
    AvailableCountry,
    PhoneNumber,
    SupportedMobileMoneyCarrier,
)
from app.accounts.tests import factories as f


class AccountTestCase(TestCase):
    def setUp(self):
        self.account: Account = f.AccountFactory.create()
        self.account_number = self.account.number

    def test_it_should_have_account_number(self):
        self.assertIsNotNone(self.account.number)

    def test_it_assert_should_not_change_account_number(self):
        self.account.save()
        self.assertEqual(self.account_number, self.account.number)

    def test_it_should_have_payment_code(self):
        self.assertIsNotNone(self.account.payment_code)

    @patch("app.accounts.models.make_pin")
    def test_it_should_set_pin(self, mocked_make_pin: MagicMock):
        pin = "4352"
        mocked_make_pin.return_value = "ZERFZF43234"
        self.account.set_pin(pin)
        mocked_make_pin.assert_called_once_with(pin)

    @patch("app.accounts.models.check_pin")
    def test_it_should_verify_pin(self, mocked_checked_pin: MagicMock):
        pin = "4352"
        self.account.verify_pin(pin)
        mocked_checked_pin.assert_called_once_with(self.account.pin, pin)

    @patch("app.accounts.models.Account.save")
    def test_it_set_balance(self, mocked_save: MagicMock):
        self.account.set_balance(3000)

        mocked_save.assert_called_once()

    @patch("app.accounts.models.Account.set_balance")
    def test_it_shoud_debit_account(self, mocked_set_balance: MagicMock):
        charged_amount = 1000
        self.account.debit(charged_amount)
        expected_balance = float(self.account.balance - charged_amount)

        mocked_set_balance.assert_called_once_with(expected_balance)

    @patch("app.accounts.models.Account.set_balance")
    def test_it_should_credit_account(self, mocked_set_balance: MagicMock):
        amount = 1000
        expected_balance = float(amount + self.account.balance)
        self.account.credit(amount)

        mocked_set_balance.assert_called_once_with(expected_balance)

    def test_it_check_balance(self):
        self.assertEqual(-1, self.account.check_balance(2000))


class PhoneNumberTestCase(TestCase):
    def setUp(self):
        self.account: Account = f.AccountFactory.create()
        carrier = f.CarrierFactory.create(country=self.account.country)

        self.phone_number_payload = {
            "phone_number": "698049742",
            "account_id": self.account.id,
            "carrier_id": carrier.id,
        }

    def test_it_should_create_phone_number_instance(self):
        phone_number: PhoneNumber = PhoneNumber.create(**{**self.phone_number_payload})

        self.assertTrue(isinstance(phone_number, PhoneNumber))


class SupportedMobileMoneyCarrierTestCase(TestCase):
    def setUp(self):
        pass

    def test_it_object_creation(self):
        country: AvailableCountry = f.AvailableCountryFactory.create()
        carrier = SupportedMobileMoneyCarrier.objects.create(
            name="Orange", country=country
        )

        self.assertEqual(carrier.code, f"{carrier.name}_{country.iso_code}".lower())
