import datetime
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from app.accounts.models import Account, AvailableCountry, PassCode, PhoneNumber
from app.accounts.tests import factories as f


class PassCodeTestCase(TransactionTestCase):
    def setUp(self):
        self.intl_phone_number = "+235698049742"

    @patch("app.accounts.models.PassCode.send_code")
    def test_it_should_create_and_send_new_passcode(self, mocked_send_code: MagicMock):
        passcode: PassCode = PassCode.create(self.intl_phone_number)

        mocked_send_code.assert_called_once()

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(passcode.intl_phone_number, self.intl_phone_number)
        self.assertIsInstance(passcode.next_verif_attempt_on, datetime.datetime)
        self.assertIsInstance(passcode.next_passcode_on, datetime.datetime)

    @patch("app.accounts.models.PassCode.send_code")
    def test_it_should_expire_previous_code_before_create_one(
        self, mocked_send_code: MagicMock
    ):
        PassCode.create(self.intl_phone_number)
        PassCode.create(self.intl_phone_number)

        mocked_send_code.assert_called()

        qs = PassCode.objects.filter(intl_phone_number=self.intl_phone_number)
        passcode1: PassCode = qs.first()
        passcode2: PassCode = qs.last()

        self.assertEqual(qs.count(), 2)
        self.assertTrue(passcode1.expired)
        self.assertFalse(passcode2.expired)

    def test_it_should_expired_code(self):
        passcode: PassCode = f.PassCodeFactory.build()
        passcode.set_expired()

        self.assertTrue(passcode.expired)

    def test_it_should_set_verified_passcode(self):
        passcode: PassCode = f.PassCodeFactory.build()

        self.assertFalse(passcode.verified)
        passcode.set_verified()
        self.assertTrue(passcode.verified)

    @patch("app.accounts.models.PassCode.set_verified")
    @patch("app.accounts.models.PassCode.increate_next_attempt_time")
    def test_it_should_not_verified_passcode(
        self,
        mocked_increate_next_attempt_time: MagicMock,
        mocked_set_verified: MagicMock,
    ):
        passcode: PassCode = f.PassCodeFactory.build()

        verified = passcode.verify("345432")

        self.assertFalse(verified)
        mocked_increate_next_attempt_time.assert_called_once()
        mocked_set_verified.assert_not_called()

    @patch("app.accounts.models.PassCode.set_verified")
    @patch("app.accounts.models.PassCode.increate_next_attempt_time")
    def test_it_should_verified_passcode(
        self,
        mocked_increate_next_attempt_time: MagicMock,
        mocked_set_verified: MagicMock,
    ):
        passcode: PassCode = f.PassCodeFactory.build()

        verified = passcode.verify("987657")

        self.assertTrue(verified)
        mocked_increate_next_attempt_time.assert_not_called()
        mocked_set_verified.assert_called_once()

    @patch("app.accounts.models.compute_next_verif_attempt_time")
    def test_it_should_increase_next_attempt_date(self, mocked_compute: MagicMock):
        passcode: PassCode = f.PassCodeFactory.build()
        time_now = timezone.now()
        mocked_compute.return_value = time_now

        passcode.increate_next_attempt_time()

        mocked_compute.assert_called_once_with(passcode.attempt_count)
        self.assertEqual(passcode.next_verif_attempt_on, time_now)
        self.assertEqual(passcode.attempt_count, 1)

    @patch("app.accounts.models.compute_next_verif_attempt_time")
    def test_it_should_increase_next_passcode_on_along_with_verify_on(
        self, mocked_compute: MagicMock
    ):
        passcode: PassCode = f.PassCodeFactory.build()
        time_now = timezone.now() + datetime.timedelta(minutes=5)
        mocked_compute.return_value = time_now

        passcode.increate_next_attempt_time()

        self.assertEqual(passcode.next_passcode_on, time_now)


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


class PhoneNumberTestCase(TestCase):
    def setUp(self):
        self.account: Account = f.AccountFactory.create()

        self.phone_number_payload = {
            "phone_number": "698049742",
            "country_iso_code": "CM",
            "account_id": self.account.id,
        }

    def test_it_should_create_phone_number_instance(self):
        phone_number: PhoneNumber = PhoneNumber.create(**{**self.phone_number_payload})

        self.assertTrue(isinstance(phone_number, PhoneNumber))

    def test_it_should_set_phone_number_as_primary(self):
        phone_number: PhoneNumber = PhoneNumber.create(**{**self.phone_number_payload})

        self.assertFalse(phone_number.is_primary)

        phone_number.set_primary()

        self.assertTrue(phone_number.is_primary)

    def test_it_should_created_verified_phone_number(self):
        phone_number: PhoneNumber = PhoneNumber.create(**self.phone_number_payload)

        self.assertTrue(phone_number.is_verified)
        self.assertEqual(
            phone_number.number, self.phone_number_payload.get("phone_number")
        )
