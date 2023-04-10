from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from app.accounts.models import AvailableCountry, PassCode, PhoneNumber, User as UserModel

User: UserModel = get_user_model()

class PassCodeTestCase(TransactionTestCase):
    def setUp(self):
        self.payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM',
            'code': '987657',
            'sent_date': timezone.now()
        }
        self.passcode_payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM'
        }

    def test_it_should_not_create_passcode_if_one_required_fields_miss(self):
        with self.assertRaises(IntegrityError):
            del self.payload['phone_number']
            PassCode.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            del self.payload['country_iso_code']
            PassCode.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            del self.payload['code']
            PassCode.objects.create(**self.payload)

    def test_it_should_create_passcode(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)

        self.assertTrue(isinstance(passcode, PassCode))
        self.assertEqual(PassCode.objects.count(), 1)
        self.assertEqual(passcode.phone_number, self.payload['phone_number'])
        self.assertEqual(passcode.country_iso_code, self.payload['country_iso_code'])
        self.assertEqual(passcode.code, self.payload['code'])

    @patch('app.accounts.models.PassCode.send_code')
    def test_it_should_expire_previous_code_before_create_one(self, mocked_send_code: MagicMock):
        PassCode.create(**self.passcode_payload)

        with patch('app.accounts.models.PassCode.waiting_time_expired') as mocked_waiting_time:
            mocked_waiting_time.return_value = True
            PassCode.create(**self.passcode_payload)

            qs = PassCode.objects.filter(**self.passcode_payload)
            first_passcode: PassCode = qs.first()
            last_passcode: PassCode = qs.last()

            self.assertEqual(qs.count(), 2)
            self.assertTrue(first_passcode.expired)
            self.assertFalse(last_passcode.expired)

    def test_it_should_have_default_waiting_time(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)

        self.assertTrue(passcode.waiting_time is not None)
        self.assertEqual(passcode.waiting_time, settings.DEFAULT_WAITING_TIME_SECONDS)


    def test_it_should_expired_code(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)
        passcode.set_expired()

        self.assertTrue(passcode.expired)

    def test_it_should_return_remaining_time_seconds(self):
        passcode: PassCode = PassCode.objects.create(**self.payload)
        r_time = passcode.get_remaining_time()

        self.assertTrue(isinstance(r_time, float))

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

class UserAdminTestCase(TestCase):
    def setUp(self):
        self.email = 'test.email@vulipay.com'
        self.password = '1342345'

    # need to be redefine to have a great separation of concerns
    # test manager methods in test_managers file
    def test_it_should_create_valid_superuser(self):
        with patch("app.accounts.models.User.set_password") as mocked_make_password:
            user: UserModel = User.objects.create_superuser(self.email, self.password)

            self.assertTrue(isinstance(user, UserModel))
            self.assertTrue(user.is_active)
            self.assertTrue(user.is_staff)
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.password is not None)
            self.assertEqual(user.email, self.email)
            self.assertTrue(user.first_name is None)
            self.assertTrue(user.last_name is None)

            mocked_make_password.assert_called_once_with(self.password)

    def test_it_should_not_create_superuser_if_email_is_missing(self):
        with patch("app.accounts.models.User.set_password") as mocked_make_password:
            with self.assertRaises(ValueError):
                User.objects.create_superuser(None, None)
            mocked_make_password.assert_not_called()


class UserTestCase(TestCase):
    def setUp(self):
        return super().setUp()


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

    def test_should_not_login_with_no_primary_number(self):
        pass