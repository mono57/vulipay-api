from unittest.mock import Mock, patch

from django.test import TestCase, TransactionTestCase
from rest_framework import exceptions

from app.accounts.models import Account
from app.accounts.tests.factories import *
from app.accounts.tests.factories import AvailableCountryFactory
from app.transactions.api import serializers
from app.transactions.models import Transaction
from app.transactions.tests.factories import (
    PaymentMethodTypeFactory,
    TransactionFactory,
    TransactionFeeFactory,
)


class BaseTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.BasePaymentTransactionSerializer

    def test_it_should_not_validate_for_wrong_amount(self):
        data = {"amount": 0}
        serializer = self.serializer(data=data)

        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("amount", serializer.errors)

        data["amount"] = -200

        serializer = self.serializer(data=data)
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("amount", serializer.errors)


class P2PTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.P2PTransactionSerializer

    def test_it_should_not_validate_if_body_empty(self):
        serializer = self.serializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_it_should_validate_serializer(self):
        data = {"amount": 30}
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())


class TransactionDetailsSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer = serializers.TransactionDetailsSerializer
        self.receiver_account = AccountFactory.create()
        self.transaction = Transaction.create_P2P_transaction(
            2000, receiver_account=self.receiver_account
        )

    def test_it_should_serialize_P2P_transaction(self):
        serializer = self.serializer(self.transaction)

        data = serializer.data

        self.assertIn("payer_account", data)
        self.assertIsNotNone(data.get("reference"))
        self.assertIsNotNone(data.get("status"))
        self.assertIsNotNone(data.get("type"))
        self.assertIsNotNone(data.get("amount"))
        self.assertIsNotNone(data.get("receiver_account"))
        self.assertIn("charged_amount", data)
        self.assertIn("calculated_fee", data)


class MPTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.MPTransactionSerializer
        self.receiver_account: Account = AccountFactory.create()
        self.fake_amount = float(2000)

    def test_it_should_not_validate_transaction_for_not_existing_account(self):
        data = {"amount": self.fake_amount, "receiver_account": "23542"}
        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("receiver_account", s.errors)

    def test_it_should_validate_transaction(self):
        data = {
            "amount": self.fake_amount,
            "receiver_account": self.receiver_account.number,
        }

        s = self.serializer(data=data)
        self.assertTrue(s.is_valid())

    def test_it_should_create_MP_transaction(self):
        payer_account = AccountFactory.create(
            phone_number="698238382", country=self.receiver_account.country
        )
        data = {
            "amount": self.fake_amount,
            "receiver_account": self.receiver_account.number,
        }
        s = self.serializer(data=data)
        s.is_valid()

        with patch(
            "app.transactions.models.Transaction.create_MP_transaction"
        ) as mocked_create_MP_transaction:
            validated_data = {
                **data,
                "receiver_account": self.receiver_account,
                "payer_account": payer_account,
            }
            s.create(validated_data)

            mocked_create_MP_transaction.assert_called_once_with(
                amount=self.fake_amount,
                receiver_account=self.receiver_account,
                payer_account=payer_account,
            )


class CashOutTransactionSerializerTestCase(TransactionTestCase):
    def setUp(self) -> None:
        self.account: Account = AccountFactory.create(balance=10000)
        self.country = self.account.country
        carrier = CarrierFactory.create(country=self.country)
        PhoneNumberFactory.create(account=self.account, carrier=carrier)

    def test_it_should_validate(self):
        payload = {"intl_phone_number": "237698049741", "amount": 5000, "pin": "2324"}
        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )
        self.assertTrue(s.is_valid())

    def test_it_should_raise_un_verified_phone_number(self):
        payload = {"intl_phone_number": "237698049742", "amount": 5000, "pin": "2324"}
        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )
        self.assertFalse(s.is_valid())

    def test_it_should_raise_insufficient_balance(self):
        TransactionFeeFactory.create_co_transaction_fee(country=self.country)
        payload = {"intl_phone_number": "237698049741", "amount": 10000, "pin": "2324"}

        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )

        assert s.is_valid() == True

        validated_data = {**payload}

        with self.assertRaises(exceptions.PermissionDenied):
            s.create(validated_data)

    def test_it_should_initiate_co_transaction(self):
        TransactionFeeFactory.create_co_transaction_fee(country=self.country)
        payload = {"intl_phone_number": "237698049741", "amount": 5000, "pin": "2324"}

        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )

        assert s.is_valid() == True

        validated_data = {**payload}

        tx = s.create(validated_data)

        self.assertIsInstance(tx, Transaction)


class PaymentMethodTypeSerializerTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create(name="Cameroon", iso_code="CM")

        # Create card payment method type
        self.visa_type = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Visa", country=self.country
        )

        # Create mobile money payment method type
        self.mtn_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="MTN Mobile Money", country=self.country
            )
        )

    def test_payment_method_type_serialization(self):
        """Test that PaymentMethodTypeSerializer correctly serializes a PaymentMethodType"""
        serializer = serializers.PaymentMethodTypeSerializer(self.visa_type)
        data = serializer.data

        self.assertEqual(data["name"], "Visa")
        self.assertEqual(data["code"], "CARD_VISA")
        self.assertEqual(data["country_name"], "Cameroon")
        self.assertEqual(data["country_code"], "CM")
        self.assertIn("required_fields", data)

        # Check required fields for card payment method type
        required_fields = data["required_fields"]
        self.assertIn("cardholder_name", required_fields)
        self.assertIn("card_number", required_fields)
        self.assertIn("expiry_date", required_fields)
        self.assertIn("cvv", required_fields)
        self.assertIn("billing_address", required_fields)

    def test_mobile_money_payment_method_type_serialization(self):
        """Test that PaymentMethodTypeSerializer correctly serializes a mobile money PaymentMethodType"""
        serializer = serializers.PaymentMethodTypeSerializer(self.mtn_type)
        data = serializer.data

        self.assertEqual(data["name"], "MTN Mobile Money")
        self.assertEqual(data["code"], "MOBILE_MTN_MOBILE_MONEY")
        self.assertEqual(data["country_name"], "Cameroon")
        self.assertEqual(data["country_code"], "CM")
        self.assertIn("required_fields", data)

        # Check required fields for mobile money payment method type
        required_fields = data["required_fields"]
        self.assertIn("provider", required_fields)
        self.assertIn("mobile_number", required_fields)

        # Check that the provider help text includes the name of the payment method type
        self.assertIn("MTN Mobile Money", required_fields["provider"]["help_text"])


class PaymentMethodSerializerTestCase(TestCase):
    """Test case for the PaymentMethodSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory.create()
        self.country = AvailableCountryFactory.create(
            name="Cameroon", iso_code="CM", dial_code="237"
        )

        # Create payment method types
        self.visa_type = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Visa", code="CARD_VISA", country=self.country
        )
        self.mtn_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="MTN Mobile Money", code="MOBILE_MTN", country=self.country
            )
        )

    def test_payment_method_serializer_with_payment_method_type(self):
        """Test that PaymentMethodSerializer correctly handles payment_method_type field."""
        data = {
            "name": "My Visa Card",
            "type": "card",  # Use lowercase as per model choices
            "card_number": "4111111111111111",
            "cardholder_name": "John Doe",
            "expiry_date": "12/2025",  # Fix the format to MM/YYYY
            "cvv": "123",
            "billing_address": "123 Main St",
            "payment_method_type": self.visa_type.id,
        }

        # Mock the request context
        mock_request = Mock()
        mock_request.user = self.user

        serializer = serializers.PaymentMethodSerializer(
            data=data, context={"request": mock_request, "user": self.user}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # Check that payment_method_type is included in validated data
        self.assertEqual(
            serializer.validated_data["payment_method_type"].id, self.visa_type.id
        )

        # We won't test save() since it requires more complex mocking


class CardPaymentMethodSerializerTestCase(TestCase):
    """Test case for the CardPaymentMethodSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory.create()
        self.country = AvailableCountryFactory.create(
            name="Cameroon", iso_code="CM", dial_code="237"
        )

        # Create payment method type
        self.visa_type = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Visa", code="CARD_VISA", country=self.country
        )

    def test_card_payment_method_serializer_with_payment_method_type(self):
        """Test that CardPaymentMethodSerializer correctly handles payment_method_type field."""
        data = {
            "name": "My Visa Card",
            "card_number": "4111111111111111",
            "cardholder_name": "John Doe",
            "expiry_date": "12/2025",  # Fix the format to MM/YYYY
            "cvv": "123",
            "billing_address": "123 Main St",
            "payment_method_type": self.visa_type.id,
        }

        # Mock the request context
        mock_request = Mock()
        mock_request.user = self.user

        serializer = serializers.CardPaymentMethodSerializer(
            data=data, context={"request": mock_request, "user": self.user}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # Check that payment_method_type is included in validated data
        self.assertEqual(
            serializer.validated_data["payment_method_type"].id, self.visa_type.id
        )

        # We won't test save() since it requires more complex mocking


class MobileMoneyPaymentMethodSerializerTestCase(TestCase):
    """Test case for the MobileMoneyPaymentMethodSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory.create()
        self.country = AvailableCountryFactory.create(
            name="Ghana",  # Use a different country
            iso_code="GH",
            dial_code="233",  # Different dial code
        )

        # Create payment method type
        self.mtn_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="MTN Mobile Money", code="MOBILE_MTN", country=self.country
            )
        )

        # Mock the phone number instead of creating it
        self.phone_number = Mock()
        self.phone_number.id = 1
        self.phone_number.number = "+233612345678"
        self.phone_number.country = self.country
        self.phone_number.is_verified = True

    def test_mobile_money_payment_method_serializer_with_payment_method_type(self):
        """Test that MobileMoneyPaymentMethodSerializer correctly handles payment_method_type field."""
        data = {
            "name": "My MTN Mobile Money",
            "provider": "MTN",
            "mobile_number": self.phone_number.id,  # Use the phone number ID
            "payment_method_type": self.mtn_type.id,
        }

        # Mock the request context
        mock_request = Mock()
        mock_request.user = self.user

        # Mock the PhoneNumber.objects.get method
        with patch("app.accounts.models.PhoneNumber.objects.get") as mock_get:
            mock_get.return_value = self.phone_number

            serializer = serializers.MobileMoneyPaymentMethodSerializer(
                data=data, context={"request": mock_request, "user": self.user}
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)

            # Check that payment_method_type is included in validated data
            self.assertEqual(
                serializer.validated_data["payment_method_type"].id, self.mtn_type.id
            )

        # We won't test save() since it requires more complex mocking
