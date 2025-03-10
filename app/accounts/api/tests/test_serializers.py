import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from app.accounts.api.serializers import (
    AccountBalanceSerializer,
    AccountInfoUpdateModelSerializer,
    AddPhoneNumberSerializer,
    CreatePasscodeSerializer,
    PinCreationSerializer,
    UserFullNameUpdateSerializer,
    VerifyPassCodeSerializer,
)
from app.accounts.models import Account, AvailableCountry
from app.accounts.tests.factories import (
    AccountFactory,
    AvailableCountryFactory,
    CarrierFactory,
)

User = get_user_model()


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


class UserFullNameUpdateSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test_serializer@example.com",
            password="testpassword123",
            full_name="Original Name",
        )

        self.serializer_data = {"full_name": "Updated Full Name"}

        self.serializer = UserFullNameUpdateSerializer(
            instance=self.user, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_empty_full_name(self):
        """Test that the serializer rejects empty full_name"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_whitespace_full_name(self):
        """Test that the serializer rejects full_name with only whitespace"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": "   "}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_update_user(self):
        self.serializer.is_valid()
        self.serializer.save()

        updated_user = User.objects.get(pk=self.user.pk)
        self.assertEqual(updated_user.full_name, self.serializer_data["full_name"])

    def test_serializer_output(self):
        """Test that the serializer output contains the correct fields"""
        serializer = UserFullNameUpdateSerializer(instance=self.user)
        data = serializer.data

        self.assertIn("full_name", data)
        self.assertEqual(data["full_name"], self.user.full_name)
