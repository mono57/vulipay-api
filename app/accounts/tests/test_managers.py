import datetime
from unittest.mock import patch

from django.test import TestCase

from app.accounts.models import AvailableCountry, PassCode, PhoneNumber, Account
from app.accounts.managers import *
from app.accounts.tests.factories import AvailableCountryFactory

class AccountManagerTestCase(TestCase):
    def setUp(self):
        pass

    def test_it_should_generate_account_number(self):
        number = AccountManager.generate_account_number()

        self.assertIsNotNone(number)
        self.assertIsInstance(number, str)
        self.assertTrue(number.isdigit())
        self.assertTrue(len(number), 16)


class PassCodeManagerTestCase(TestCase):
    def setUp(self):
        self.phone_number = '698493823'
        self.country_iso_code = "CM"

        self.passcode_payload = {
            "phone_number": self.phone_number,
            "country_iso_code": self.country_iso_code,
            "code": "234543",
            "sent_on": timezone.now(),
            "next_passcode_on": timezone.now(),
            "next_verif_attempt_on": timezone.now(),
        }
        PassCode.objects.create(**self.passcode_payload)

    def test_it_should_return_the_one_created_passcode(self):
        passcode:PassCode = PassCode.objects.get_last_code(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(passcode.phone_number, self.passcode_payload.get('phone_number'))
        self.assertEqual(passcode.country_iso_code, self.passcode_payload.get('country_iso_code'))
        self.assertEqual(passcode.code, self.passcode_payload.get('code'))
        self.assertEqual(PassCode.objects.count(), 1)


    def test_it_should_return_the_last_created_passcode(self):
        passcode_payload2 = {
            "phone_number": self.phone_number,
            "country_iso_code": self.country_iso_code,
            "code": "234541",
            "sent_on": timezone.now(),
            "next_passcode_on": timezone.now(),
            "next_verif_attempt_on": timezone.now(),
        }

        PassCode.objects.create(**passcode_payload2)

        passcode = PassCode.objects.get_last_code(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(passcode.phone_number, passcode_payload2.get('phone_number'))
        self.assertEqual(passcode.country_iso_code, passcode_payload2.get('country_iso_code'))
        self.assertEqual(passcode.code, passcode_payload2.get('code'))
        self.assertEqual(PassCode.objects.count(), 2)

    def test_it_should_allow_create_new_passcode(self):
        can_process, next_passcode_on = PassCode.objects.can_create_passcode(self.phone_number, self.country_iso_code)

        self.assertTrue(can_process)
        self.assertIsNone(next_passcode_on)

    def test_it_should_allow_create_new_passcode(self):
        can_process, next_passcode_on = PassCode.objects.can_create_passcode(self.phone_number, self.country_iso_code)

        self.assertTrue(can_process)
        self.assertIsNone(next_passcode_on)

    def test_it_should_not_allow_create_new_passcode(self):
        time_now = timezone.now() + datetime.timedelta(minutes=1)
        passcode_payload = {
            **self.passcode_payload,
            "phone_number": '675564466',
            "next_passcode_on": time_now,
            "next_verif_attempt_on": timezone.now(),
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_passcode_on = PassCode.objects.can_create_passcode('675564466', self.country_iso_code)

        self.assertFalse(can_process)
        self.assertIsNotNone(next_passcode_on)
        self.assertEqual(next_passcode_on, time_now)

    def test_it_should_not_allow_verify_otp(self):
        time_now = timezone.now() + datetime.timedelta(minutes=5)

        passcode_payload = {
            **self.passcode_payload,
            "phone_number": '675564466',
            "next_verif_attempt_on": time_now,
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_attempt_on = PassCode.objects.can_verify('675564466', self.country_iso_code)

        self.assertFalse(can_process)
        self.assertIsNotNone(next_attempt_on)
        self.assertEqual(next_attempt_on, time_now)

    def test_it_should_verify_otp(self):
        time_now = timezone.now()
        passcode_payload = {
            **self.passcode_payload,
            "phone_number": '675564466',
            "next_verif_attempt_on": time_now,
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_attempt_on = PassCode.objects.can_verify('675564466', self.country_iso_code)

        self.assertTrue(can_process)
        self.assertIsNone(next_attempt_on)

class PhoneNumberManagerTestCase(TestCase):
    def setUp(self):
        self.account = Account.objects.create()
        self.country: AvailableCountry = AvailableCountryFactory.create()

        self.phone_number_payload = {
            'number': '698049742',
            'carrier': 'Orange CM',
            'account': self.account,
            'country': self.country,
        }

        PhoneNumber.objects.create(**self.phone_number_payload, primary=True)
        PhoneNumber.objects.create(**{**self.phone_number_payload, 'number': '687943045'})

    def test_it_should_return_primary_phone_number(self):
        primary_phone_number: PhoneNumber = PhoneNumber.objects.get_primary(self.account)

        self.assertTrue(isinstance(primary_phone_number, PhoneNumber))
        self.assertTrue(primary_phone_number.primary)
        self.assertEqual(primary_phone_number.number, self.phone_number_payload.get('number'))

    def test_it_should_return_phone_number_account(self):
        account = PhoneNumber.objects.get_account(self.phone_number_payload.get('number'), AvailableCountryFactory.iso_code)

        self.assertTrue(isinstance(account, Account))
        self.assertEqual(self.account.id, account.id)

    def test_it_should_not_get_account_if_phone_number_not_exists(self):
        account = PhoneNumber.objects.get_account('687943041', AvailableCountryFactory.iso_code)

        self.assertTrue(account is None)
