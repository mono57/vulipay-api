from unittest.mock import MagicMock, patch
import datetime

from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.utils import timezone

from app.accounts.models import AvailableCountry, PassCode, PhoneNumber, Account

class PassCodeTestCase(TransactionTestCase):
    def setUp(self):
        self.payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM',
            'code': '987657',
            'sent_on': timezone.now(),
            'next_verif_attempt_on': timezone.now(),
            'next_passcode_on': timezone.now(),
        }
        self.passcode_payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM'
        }

    @patch('app.accounts.models.PassCode.send_code')
    def test_it_should_create_and_send_new_passcode(self, mocked_send_code: MagicMock):
        passcode: PassCode = PassCode.create(**self.passcode_payload)

        mocked_send_code.assert_called_once()

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(passcode.phone_number, self.passcode_payload['phone_number'])
        self.assertEqual(passcode.country_iso_code, self.passcode_payload['country_iso_code'])
        self.assertIsInstance(passcode.next_verif_attempt_on, datetime.datetime)
        self.assertIsInstance(passcode.next_passcode_on, datetime.datetime)

    @patch('app.accounts.models.PassCode.send_code')
    def test_it_should_expire_previous_code_before_create_one(self, mocked_send_code: MagicMock):
        PassCode.create(**self.passcode_payload)
        PassCode.create(**self.passcode_payload)

        mocked_send_code.assert_called()

        qs = PassCode.objects.filter(**self.passcode_payload)
        passcode1: PassCode = qs.first()
        passcode2: PassCode = qs.last()

        self.assertEqual(qs.count(), 2)
        self.assertTrue(passcode1.expired)
        self.assertFalse(passcode2.expired)


    def test_it_should_expired_code(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)
        passcode.set_expired()

        self.assertTrue(passcode.expired)

    def test_it_should_set_verified_passcode(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)

        self.assertFalse(passcode.verified)
        passcode.set_verified()
        self.assertTrue(passcode.verified)

    @patch('app.accounts.models.PassCode.set_verified')
    @patch('app.accounts.models.PassCode.increate_next_attempt_time')
    def test_it_should_not_verified_passcode(self, mocked_increate_next_attempt_time: MagicMock, mocked_set_verified: MagicMock):
        passcode: PassCode = PassCode.objects.create(**self.payload)

        verified = passcode.verify('345432')

        self.assertFalse(verified)
        mocked_increate_next_attempt_time.assert_called_once()
        mocked_set_verified.assert_not_called()

    @patch('app.accounts.models.PassCode.set_verified')
    @patch('app.accounts.models.PassCode.increate_next_attempt_time')
    def test_it_should_verified_passcode(self, mocked_increate_next_attempt_time: MagicMock, mocked_set_verified: MagicMock):
        passcode: PassCode = PassCode.objects.create(**self.payload)

        verified = passcode.verify('987657')

        self.assertTrue(verified)
        mocked_increate_next_attempt_time.assert_not_called()
        mocked_set_verified.assert_called_once()

    @patch('app.accounts.models.compute_next_verif_attempt_time')
    def test_it_should_increase_next_attempt_date(self, mocked_compute: MagicMock):
        passcode: PassCode = PassCode.objects.create(**self.payload)
        time_now = timezone.now()
        mocked_compute.return_value = time_now

        passcode.increate_next_attempt_time()

        mocked_compute.assert_called_once_with(passcode.attempt_count)
        self.assertEqual(passcode.next_verif_attempt_on, time_now)
        self.assertEqual(passcode.attempt_count, 1)

    @patch('app.accounts.models.compute_next_verif_attempt_time')
    def test_it_should_increase_next_passcode_on_along_with_verify_on(self, mocked_compute: MagicMock):
        passcode: PassCode = PassCode.objects.create(**self.payload)
        time_now = timezone.now() + datetime.timedelta(minutes=5)
        mocked_compute.return_value = time_now

        passcode.increate_next_attempt_time()

        self.assertEqual(passcode.next_passcode_on, time_now)



class AvailableCountryTestCase(TransactionTestCase):
    def setUp(self):
        self.payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "REGEX",
        }

    def test_it_should_not_create_country_if_one_required_field_miss(self):
        with self.assertRaises(IntegrityError):
            del self.payload['name']
            AvailableCountry.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            del self.payload['dial_code']
            AvailableCountry.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            del self.payload['iso_code']
            AvailableCountry.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            del self.payload['phone_number_regex']
            AvailableCountry.objects.create(**self.payload)

    def test_it_should_create_country(self):
        country: AvailableCountry = AvailableCountry.objects.create(**self.payload)

        self.assertTrue(isinstance(country, AvailableCountry))
        self.assertEqual(AvailableCountry.objects.count(), 1)
        self.assertEqual(country.name, self.payload['name'])
        self.assertEqual(country.dial_code, self.payload['dial_code'])
        self.assertEqual(country.iso_code, self.payload['iso_code'])
        self.assertEqual(country.phone_number_regex, self.payload['phone_number_regex'])

    def test_it_should_not_create_country_twice(self):
        AvailableCountry.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            AvailableCountry.objects.create(**self.payload)

class AccountTestCase(TestCase):
    def setUp(self):
        self.account: Account = Account.objects.create()
        self.account_number = self.account.number

    def test_it_should_have_account_number(self):
        self.assertIsNotNone(self.account.number)

    def test_it_assert_should_not_change_account_number(self):
        self.account.save()
        self.assertEqual(self.account_number, self.account.number)

    def test_it_should_have_payment_code(self):
        self.assertIsNotNone(self.account.payment_code)

class PhoneNumberTestCase(TestCase):
    def setUp(self):
        self.country_payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "REGEX",
        }

        self.phone_number_payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM'
        }

        AvailableCountry.objects.create(**self.country_payload)

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
        self.assertEqual(phone_number.number, self.phone_number_payload.get('phone_number'))

    def test_it_should_create_account_for_new_phone_number(self):
        phone_number: PhoneNumber = PhoneNumber.create(**{**self.phone_number_payload})

        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Account.objects.last(), phone_number.account)
