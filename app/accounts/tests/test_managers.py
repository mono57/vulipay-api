import datetime
from unittest.mock import patch

from django.test import TestCase

from app.accounts.models import PassCode
from app.accounts.managers import *
from app.accounts.tests import factories as f

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
        self.intl_phone_number = '237698493823'
        self.intl_phonenumber2 = '237675564466'

        self.passcode_payload = {
            "intl_phone_number": self.intl_phone_number,
            "code": "234543",
            "sent_on": timezone.now(),
            "next_passcode_on": timezone.now(),
            "next_verif_attempt_on": timezone.now(),
        }
        f.PassCodeFactory.create(intl_phone_number=self.intl_phone_number, code="234543")

    def test_it_should_return_the_one_created_passcode(self):
        passcode:PassCode = PassCode.objects.get_last_code(self.intl_phone_number)

        self.assertEqual(passcode.intl_phone_number, self.passcode_payload.get('intl_phone_number'))
        self.assertEqual(passcode.code, self.passcode_payload.get('code'))
        self.assertEqual(PassCode.objects.count(), 1)


    def test_it_should_return_the_last_created_passcode(self):
        passcode_payload2 = {
            "code": "234541",
            "intl_phone_number": self.intl_phone_number
        }

        f.PassCodeFactory.create(**passcode_payload2)

        passcode: PassCode = PassCode.objects.get_last_code(self.intl_phone_number)

        self.assertEqual(passcode.intl_phone_number, passcode_payload2.get('intl_phone_number'))
        self.assertEqual(passcode.code, passcode_payload2.get('code'))
        self.assertEqual(PassCode.objects.count(), 2)

    def test_it_should_allow_create_new_passcode(self):
        can_process, next_passcode_on = PassCode.objects.can_create_passcode(self.intl_phone_number)

        self.assertTrue(can_process)
        self.assertIsNone(next_passcode_on)

    def test_it_should_allow_create_new_passcode(self):
        can_process, next_passcode_on = PassCode.objects.can_create_passcode(self.intl_phone_number)

        self.assertTrue(can_process)
        self.assertIsNone(next_passcode_on)

    def test_it_should_not_allow_create_new_passcode(self):
        time_now = timezone.now() + datetime.timedelta(minutes=1)
        passcode_payload = {
            **self.passcode_payload,
            "intl_phone_number": self.intl_phonenumber2,
            "next_passcode_on": time_now,
            "next_verif_attempt_on": timezone.now(),
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_passcode_on = PassCode.objects.can_create_passcode(self.intl_phonenumber2)

        self.assertFalse(can_process)
        self.assertIsNotNone(next_passcode_on)
        self.assertEqual(next_passcode_on, time_now)

    def test_it_should_not_allow_verify_otp(self):
        time_now = timezone.now() + datetime.timedelta(minutes=5)

        passcode_payload = {
            **self.passcode_payload,
            "intl_phone_number": self.intl_phonenumber2,
            "next_verif_attempt_on": time_now,
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_attempt_on = PassCode.objects.can_verify(self.intl_phonenumber2)

        self.assertFalse(can_process)
        self.assertIsNotNone(next_attempt_on)
        self.assertEqual(next_attempt_on, time_now)

    def test_it_should_verify_otp(self):
        time_now = timezone.now()
        passcode_payload = {
            **self.passcode_payload,
            "intl_phone_number": self.intl_phonenumber2,
            "next_verif_attempt_on": time_now,
        }
        PassCode.objects.create(**passcode_payload)
        can_process, next_attempt_on = PassCode.objects.can_verify(self.intl_phonenumber2)

        self.assertTrue(can_process)
        self.assertIsNone(next_attempt_on)
