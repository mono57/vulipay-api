from unittest.mock import patch
import datetime

from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from app.accounts.api.serializers import CreatePasscodeSerializer, VerifyPassCodeSerializer
from app.accounts.models import AvailableCountry, PassCode

class CreatePasscodeSerializerTestCase(TestCase):
    payload = {
        "name": "Cameroun",
        "dial_code": "237",
        "iso_code": "CM",
        "phone_number_regex": "",
    }

    def setUp(self):
        self.serializer = CreatePasscodeSerializer
        AvailableCountry.objects.create(**self.payload)

    def test_it_should_not_validate_if_any_field_missing(self):
        data = {}
        s = self.serializer(data=data)

        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)
        self.assertIn("country_iso_code", s.errors)

    def test_it_should_not_validate_if_country_not_found(self):
        data = {
            "phone_number": 60493823,
            "country_iso_code": 2323
        }

        s = self.serializer(data=data)

        self.assertFalse(s.is_valid())
        self.assertIn("country_iso_code", s.errors)

    def test_it_should_not_validate_if_phone_number_is_invalid(self):
        data = {
            "phone_number": 00000000,
            "country_iso_code": "CM"
        }

        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)

    def test_it_should_serialize_without_error(self):
        data = {
            "phone_number": '698049742',
            "country_iso_code": "CM"
        }

        s = self.serializer(data=data)
        self.assertTrue(s.is_valid())

class VerifyPassCodeSerializerTestCase(TestCase):
    def setUp(self):
        self.data = {
            "phone_number": '698493823',
            "country_iso_code": "CM",
            "code": "234543"
        }
        # self.intl_phonenumber = f'+237{self.data.get('phone_number')}'
        country_payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "",
        }
        self.passcode_payload = {
            "intl_phonenumber": '+237698493823',
            "code": "234543",
            "sent_on": datetime.datetime.now(timezone.utc),
            'next_verif_attempt_on': timezone.now(),
            'next_passcode_on': timezone.now(),
        }
        self.serializer = VerifyPassCodeSerializer
        AvailableCountry.objects.create(**country_payload)

    def test_it_should_not_validate_if_code_is_missing(self):
        del self.data['code']
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual('required', s.errors.get('code')[0].code)

    def test_it_should_not_validate_if_code_not_digits(self):
        self.data['code'] = 'ER3353'
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual('invalid_code', s.errors.get('code')[0].code)

    def test_it_should_not_validate_if_bad_code_length(self):
        self.data['code'] = '3353'
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual('invalid_code', s.errors.get('code')[0].code)

    def test_it_should_not_validate_if_passcode_has_not_found(self):
        s = self.serializer(data=self.data)

        with patch("app.accounts.models.PassCode.objects.get_last_code") as mocked_get_last_code:
            mocked_get_last_code.return_value = None

            self.assertFalse(s.is_valid())

            mocked_get_last_code.assert_called_once_with(
                self.passcode_payload.get('intl_phonenumber'))

            self.assertIn('code', s.errors)
            self.assertEqual('code_not_found', s.errors.get('code')[0].code)

    def test_it_should_verify_passcode(self):
        with patch("app.accounts.models.PassCode.objects.get_last_code") as mocked_get_last_code:
            mocked_get_last_code.return_value = PassCode.objects.create(**self.passcode_payload)

            s = self.serializer(data=self.data)

            self.assertTrue(s.is_valid())

            mocked_get_last_code.assert_called_once_with(self.passcode_payload.get('intl_phonenumber'))

    def test_it_should_not_verify_passcode_when_expired(self):
        with patch("app.accounts.models.PassCode.objects.get_last_code") as mocked_get_last_code:
            self.passcode_payload['sent_on'] = datetime.datetime.now(timezone.utc) - datetime.timedelta(seconds=40)
            mocked_get_last_code.return_value = PassCode.objects.create(**self.passcode_payload)

            s = self.serializer(data=self.data)
            self.assertFalse(s.is_valid())
            self.assertIn('code', s.errors)
            self.assertEqual('code_expired', s.errors.get('code')[0].code)

            mocked_get_last_code.assert_called_once_with(self.passcode_payload.get('intl_phonenumber'))
