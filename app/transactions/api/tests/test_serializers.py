from unittest.mock import Mock, patch

from django.test import TestCase

from app.accounts.tests.factories import *
from app.accounts.tests.factories import AvailableCountryFactory
from app.transactions.api import serializers
from app.transactions.models import TransactionType
from app.transactions.tests.factories import PaymentMethodTypeFactory


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
        self.visa_type.allowed_transactions = [
            TransactionType.CashIn,
            TransactionType.CashOut,
        ]
        self.visa_type.save()

        from app.transactions.models import TransactionFee

        TransactionFee.objects.create(
            name="Visa CashIn Fee",
            country=self.country,
            payment_method_type=self.visa_type,
            transaction_type=TransactionType.CashIn,
            fixed_fee=2.5,
            percentage_fee=None,
            fee_priority=TransactionFee.FeePriority.FIXED,
        )

        serializer = serializers.PaymentMethodTypeSerializer(self.visa_type)
        data = serializer.data

        self.assertEqual(data["name"], "Visa")
        self.assertEqual(data["code"], "CARD_VISA")
        self.assertEqual(data["country_name"], "Cameroon")
        self.assertEqual(data["country_code"], "CM")
        self.assertIn("required_fields", data)

        self.assertNotIn("allowed_transactions", data)

        # Check transactions_fees
        self.assertIn("transactions_fees", data)
        self.assertIsNotNone(data["transactions_fees"])
        self.assertEqual(len(data["transactions_fees"]), 1)
        self.assertEqual(
            data["transactions_fees"][0]["transaction_type"], TransactionType.CashIn
        )
        self.assertEqual(data["transactions_fees"][0]["fee"], 2.5)
        self.assertEqual(data["transactions_fees"][0]["fee_type"], "fixed")

        required_fields = data["required_fields"]
        self.assertIn("cardholder_name", required_fields)
        self.assertIn("card_number", required_fields)
        self.assertIn("expiry_date", required_fields)
        self.assertIn("cvv", required_fields)
        self.assertIn("billing_address", required_fields)

    def test_mobile_money_payment_method_type_serialization(self):
        serializer = serializers.PaymentMethodTypeSerializer(self.mtn_type)
        data = serializer.data

        self.assertEqual(data["name"], "MTN Mobile Money")
        self.assertEqual(data["code"], "MOBILE_MTN_MOBILE_MONEY")
        self.assertEqual(data["country_name"], "Cameroon")
        self.assertEqual(data["country_code"], "CM")
        self.assertIn("required_fields", data)

        required_fields = data["required_fields"]
        self.assertIn("provider", required_fields)
        self.assertIn("mobile_number", required_fields)

        # Check that the provider help text includes the name of the payment method type
        self.assertIn("MTN Mobile Money", required_fields["provider"]["help_text"])

    def test_payment_method_type_serialization_with_transaction_type(self):
        self.visa_type.allowed_transactions = [
            TransactionType.CashIn,
            TransactionType.CashOut,
            TransactionType.P2P,
        ]
        self.visa_type.save()

        from app.transactions.models import TransactionFee

        TransactionFee.objects.create(
            name="Visa CashIn Fee",
            country=self.country,
            payment_method_type=self.visa_type,
            transaction_type=TransactionType.CashIn,
            fixed_fee=2.5,
            percentage_fee=None,
            fee_priority=TransactionFee.FeePriority.FIXED,
        )

        TransactionFee.objects.create(
            name="Visa P2P Fee",
            country=self.country,
            payment_method_type=self.visa_type,
            transaction_type=TransactionType.P2P,
            fixed_fee=None,
            percentage_fee=1.5,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

        # Now we should get all transaction fees as a list
        serializer = serializers.PaymentMethodTypeSerializer(self.visa_type)
        data = serializer.data

        self.assertIn("transactions_fees", data)
        self.assertIsNotNone(data["transactions_fees"])
        self.assertEqual(len(data["transactions_fees"]), 2)

        # Check that both transaction fees are present
        fee_types = {fee["transaction_type"]: fee for fee in data["transactions_fees"]}

        self.assertIn(TransactionType.CashIn, fee_types)
        self.assertEqual(fee_types[TransactionType.CashIn]["fee"], 2.5)
        self.assertEqual(fee_types[TransactionType.CashIn]["fee_type"], "fixed")

        self.assertIn(TransactionType.P2P, fee_types)
        self.assertEqual(fee_types[TransactionType.P2P]["fee"], 1.5)
        self.assertEqual(fee_types[TransactionType.P2P]["fee_type"], "percentage")


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
