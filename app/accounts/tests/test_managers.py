import datetime
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from app.accounts.models import AvailableCountry, PassCode, PhoneNumber
from app.accounts.managers import *
from app.accounts.tests.factories import AvailableCountryFactory

User = get_user_model()

class UserManagerTestCase(TestCase):
    def setUp(self):
        self.user_payload = {
            'email': 'test@email.com',
            'password': 'testPassword1'
        }

    def test_it_should_create_a_superuser(self):
        with patch("app.accounts.models.User.set_password") as mocked_set_password:
            user = User.objects.create_superuser(**self.user_payload)

            mocked_set_password.assert_called_once_with(self.user_payload.get('password'))

            self.assertTrue(isinstance(user, User))
            self.assertTrue(user.is_active)
            self.assertTrue(user.is_staff)
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.password is not None)
            self.assertEqual(User.objects.count(), 1)

    # def test_it_should_not_create_superadmin_for_wrong_email(self):
    #     with patch("app.accounts.models.User.set_password") as mocked_set_password:
    #         self.user_payload['email'] = 'test'

    #         # with self.assertRaises(ValueError):
    #         User.objects.create_superuser(**self.user_payload)
    #         self.assertEqual(User.objects.count(), 0)


class PassCodeManagerTestCase(TestCase):
    def setUp(self):
        self.phone_number = '698493823'
        self.country_iso_code = "CM"

        self.passcode_payload = {
            "phone_number": self.phone_number,
            "country_iso_code": self.country_iso_code,
            "code": "234543",
            "sent_date": datetime.datetime.now(timezone.utc)
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
            "sent_date": datetime.datetime.now(timezone.utc)
        }

        PassCode.objects.create(**passcode_payload2)

        passcode = PassCode.objects.get_last_code(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(passcode.phone_number, passcode_payload2.get('phone_number'))
        self.assertEqual(passcode.country_iso_code, passcode_payload2.get('country_iso_code'))
        self.assertEqual(passcode.code, passcode_payload2.get('code'))
        self.assertEqual(PassCode.objects.count(), 2)

    # def test_it_should_return_true_on_check_can_verify_for_not_found_passcode(self):
    #     can_verify, _ = PassCode.objects.check_can_verify(self.phone_number, self.country_iso_code)

    #     self.assertTrue(can_verify)

    # def test_it_should_return_true_on_check_can_verify(self):
    #     PassCode.objects.create(**self.passcode_payload)

    #     can_verify, _ = PassCode.objects.check_can_verify(self.phone_number, self.country_iso_code)

        # self.assertTrue(can_verify)

    def test_it_should_return_false_on_check_can_verify(self):
        print('all passcode', PassCode.objects.all().count())
        passcode: PassCode = PassCode.objects.create(**self.passcode_payload)
        print('bef-created', passcode.created_at)
        print('bef-last_attempt_on', passcode.last_attempt_on)
        print('bef-next_attempt_on', passcode.next_attempt_on)
        passcode.verify("234542")
        print('bef-updated', passcode.updated_at)
        print('af-last_attempt_on', passcode.last_attempt_on)
        print('af-next_attempt_on', passcode.next_attempt_on)
        can_verify, next = PassCode.objects.check_can_verify(self.phone_number, self.country_iso_code)
        print('can_verify', can_verify)
        self.assertFalse(can_verify)


class PhoneNumberManagerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user()
        self.country: AvailableCountry = AvailableCountryFactory.create()

        self.phone_number_payload = {
            'number': '698049742',
            'carrier': 'Orange CM',
            'user': self.user,
            'country': self.country,
        }

        PhoneNumber.objects.create(**self.phone_number_payload, primary=True)
        PhoneNumber.objects.create(**{**self.phone_number_payload, 'number': '687943045'})

    def test_it_should_return_primary_phone_number(self):
        primary_phone_number: PhoneNumber = PhoneNumber.objects.get_primary(self.user)

        self.assertTrue(isinstance(primary_phone_number, PhoneNumber))
        self.assertTrue(primary_phone_number.primary)
        self.assertEqual(primary_phone_number.number, self.phone_number_payload.get('number'))

    def test_it_should_return_phone_number_user(self):
        user = PhoneNumber.objects.get_user(self.phone_number_payload.get('number'), AvailableCountryFactory.iso_code)

        self.assertTrue(isinstance(user, User))
        self.assertEqual(self.user.id, user.id)

    def test_it_should_return_none_if_phone_number_not_exists(self):
        user = PhoneNumber.objects.get_user('687943041', AvailableCountryFactory.iso_code)

        self.assertTrue(user is None)
