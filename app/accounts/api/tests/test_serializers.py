import datetime
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from app.accounts.api.serializers import (
    AccountBalanceSerializer,
    AccountInfoUpdateModelSerializer,
    AddPhoneNumberSerializer,
    CreatePasscodeSerializer,
    PinCreationSerializer,
    VerifyPassCodeSerializer,
)
from app.accounts.models import Account, AvailableCountry, PassCode
from app.accounts.tests.factories import (
    AccountFactory,
    AvailableCountryFactory,
    CarrierFactory,
)


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
        data = {"phone_number": 60493823, "country_iso_code": 2323}

        s = self.serializer(data=data)

        self.assertFalse(s.is_valid())
        self.assertIn("country_iso_code", s.errors)

    def test_it_should_not_validate_if_phone_number_is_invalid(self):
        data = {"phone_number": 00000000, "country_iso_code": "CM"}

        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)

    def test_it_should_serialize_without_error(self):
        data = {"phone_number": "698049742", "country_iso_code": "CM"}

        s = self.serializer(data=data)
        self.assertTrue(s.is_valid())


class VerifyPassCodeSerializerTestCase(TestCase):
    def setUp(self):
        self.data = {
            "phone_number": "698493823",
            "country_iso_code": "CM",
            "code": "234543",
        }
        country_payload = {
            "name": "Cameroun",
            "dial_code": "237",
            "iso_code": "CM",
            "phone_number_regex": "",
        }
        self.passcode_payload = {
            "intl_phone_number": "+237698493823",
            "code": "234543",
            "sent_on": datetime.datetime.now(datetime.timezone.utc),
            "next_verif_attempt_on": timezone.now(),
            "next_passcode_on": timezone.now(),
        }
        self.serializer = VerifyPassCodeSerializer
        AvailableCountry.objects.create(**country_payload)

    def test_it_should_not_validate_if_code_is_missing(self):
        del self.data["code"]
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual("required", s.errors.get("code")[0].code)

    def test_it_should_not_validate_if_code_not_digits(self):
        self.data["code"] = "ER3353"
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual("invalid_code", s.errors.get("code")[0].code)

    def test_it_should_not_validate_if_bad_code_length(self):
        self.data["code"] = "3353"
        s = self.serializer(data=self.data)

        self.assertFalse(s.is_valid())
        self.assertIn("code", s.errors)
        self.assertEqual("invalid_code", s.errors.get("code")[0].code)

    def test_it_should_not_validate_if_passcode_has_not_found(self):
        s = self.serializer(data=self.data)

        with patch(
            "app.accounts.models.PassCode.objects.get_last_code"
        ) as mocked_get_last_code:
            mocked_get_last_code.return_value = None

            self.assertFalse(s.is_valid())

            mocked_get_last_code.assert_called_once_with(
                self.passcode_payload.get("intl_phone_number")
            )

            self.assertIn("code", s.errors)
            self.assertEqual("code_not_found", s.errors.get("code")[0].code)

    def test_it_should_verify_passcode(self):
        with patch(
            "app.accounts.models.PassCode.objects.get_last_code"
        ) as mocked_get_last_code:
            mocked_get_last_code.return_value = PassCode.objects.create(
                **self.passcode_payload
            )

            s = self.serializer(data=self.data)

            self.assertTrue(s.is_valid())

            mocked_get_last_code.assert_called_once_with(
                self.passcode_payload.get("intl_phone_number")
            )

    def test_it_should_not_verify_passcode_when_expired(self):
        with patch(
            "app.accounts.models.PassCode.objects.get_last_code"
        ) as mocked_get_last_code:
            self.passcode_payload["sent_on"] = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(seconds=40)
            mocked_get_last_code.return_value = PassCode.objects.create(
                **self.passcode_payload
            )

            s = self.serializer(data=self.data)
            self.assertFalse(s.is_valid())
            self.assertIn("code", s.errors)
            self.assertEqual("code_expired", s.errors.get("code")[0].code)

            mocked_get_last_code.assert_called_once_with(
                self.passcode_payload.get("intl_phone_number")
            )


class PinCreationSerializerTestCase(TestCase):
    def setUp(self):
        self.account = AccountFactory.create()
        self.serializer = PinCreationSerializer

    def test_it_not_validate_on_mismatch_pin(self):
        data = {"pin1": "2343", "pin2": "2341"}
        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())

    def test_it_should_validate(self):
        data = {"pin1": "2343", "pin2": "2343"}
        s = self.serializer(data=data)
        self.assertTrue(s.is_valid())


class AccountBalanceSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.account_balance = float(5000)
        self.account = AccountFactory.create(balance=self.account_balance)

    def test_it_should_serializer_specified_fields(self):
        data = AccountBalanceSerializer(instance=self.account).data

        self.assertIn("balance", data)
        self.assertDictEqual(data, {"balance": self.account_balance})


class AddPhoneNumberSerializerTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()
        self.data = {
            "phone_number": "698049321",
            "carrier_code": "orange_cm",
            "country_iso_code": "CM",
        }

    def test_it_should_raise_unsupported_carrier(self):
        serializer = AddPhoneNumberSerializer(data=self.data)

        self.assertFalse(serializer.is_valid())

    def test_it_should_validate_serializer(self):
        CarrierFactory.create(country=self.country)
        serializer = AddPhoneNumberSerializer(data=self.data)

        self.assertTrue(serializer.is_valid())


class UserInfoUpdateModelSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.account_data = {
            "owner_first_name": "John",
            "owner_last_name": "Doe",
        }
        self.account = AccountFactory.create(**self.account_data)

        self.serializer_data = {
            "first_name": "Jane",
            "last_name": "Smith",
        }

        self.serializer = AccountInfoUpdateModelSerializer(
            instance=self.account, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_it_should_serialize_user_info(self):
        serializer = AccountInfoUpdateModelSerializer(instance=self.account)

        data = serializer.data

        self.assertIn("first_name", data)
        self.assertIn("last_name", data)

        self.assertEqual(data["first_name"], self.account_data["owner_first_name"])
        self.assertEqual(data["last_name"], self.account_data["owner_last_name"])

    def test_serializer_update_account(self):
        self.serializer.is_valid()
        self.serializer.save()

        updated_account = Account.objects.get(pk=self.account.pk)

        self.assertEqual(
            updated_account.owner_first_name, self.serializer_data["first_name"]
        )
        self.assertEqual(
            updated_account.owner_last_name, self.serializer_data["last_name"]
        )
