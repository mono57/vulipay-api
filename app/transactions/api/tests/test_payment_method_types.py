from unittest.mock import Mock, patch

from django.test import TestCase

from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.transactions.api import serializers
from app.transactions.tests.factories import PaymentMethodTypeFactory


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

    def test_mobile_money_payment_method_serializer_has_payment_method_type_field(self):
        """Test that MobileMoneyPaymentMethodSerializer has a payment_method_type field."""
        serializer = serializers.MobileMoneyPaymentMethodSerializer()

        # Test that payment_method_type is included in the serializer fields
        self.assertIn("payment_method_type", serializer.fields)

        # Check that the payment_method_type field has the correct queryset filter
        self.assertEqual(
            serializer.fields["payment_method_type"]
            .queryset.query.where.children[0]
            .lhs.field.name,
            "code",
        )
