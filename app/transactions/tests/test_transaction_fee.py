from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings

from app.accounts.tests.factories import AvailableCountryFactory
from app.transactions.models import TransactionFee, TransactionType
from app.transactions.tests.factories import PaymentMethodTypeFactory


class TransactionFeeModelTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()
        self.payment_method_type = PaymentMethodTypeFactory.create()

        # Clear cache before each test
        cache.clear()

        # Create test transaction fees
        self.fee_fixed = TransactionFee.objects.create(
            country=self.country,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type,
            fixed_fee=100,
            percentage_fee=None,
            fee_priority=TransactionFee.FeePriority.FIXED,
        )

        self.fee_percentage = TransactionFee.objects.create(
            country=self.country,
            transaction_type=TransactionType.CashIn,
            payment_method_type=self.payment_method_type,
            fixed_fee=None,
            percentage_fee=2.5,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

        # Create another fixed fee (instead of 'both')
        self.fee_fixed2 = TransactionFee.objects.create(
            country=self.country,
            transaction_type=TransactionType.CashOut,
            payment_method_type=self.payment_method_type,
            fixed_fee=50,
            percentage_fee=None,  # Should be automatically set to None in the save method
            fee_priority=TransactionFee.FeePriority.FIXED,
        )

        # Create a default fee with no specific payment method type
        self.default_fee = TransactionFee.objects.create(
            country=self.country,
            transaction_type=TransactionType.MP,
            payment_method_type=None,
            fixed_fee=None,
            percentage_fee=3.0,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

    def test_fee_property(self):
        """Test that the fee property returns the correct value based on fee_priority"""
        self.assertEqual(self.fee_fixed.fee, 100)
        self.assertEqual(self.fee_percentage.fee, 2.5)
        self.assertEqual(self.fee_fixed2.fee, 50)

    def test_string_representation(self):
        """Test the string representation of the model"""
        expected_str = f"{self.country.name} - {TransactionType.P2P} - {self.payment_method_type.name} - Fixed: 100"
        self.assertEqual(str(self.fee_fixed), expected_str)

        expected_str = f"{self.country.name} - {TransactionType.CashIn} - {self.payment_method_type.name} - Percentage: 2.5%"
        self.assertEqual(str(self.fee_percentage), expected_str)

        expected_str = f"{self.country.name} - {TransactionType.CashOut} - {self.payment_method_type.name} - Fixed: 50"
        self.assertEqual(str(self.fee_fixed2), expected_str)

        expected_str = (
            f"{self.country.name} - {TransactionType.MP} - All - Percentage: 3.0%"
        )
        self.assertEqual(str(self.default_fee), expected_str)

    def test_get_inclusive_amount(self):
        """Test the get_inclusive_amount class method"""
        fee = TransactionFee.get_inclusive_amount(
            transaction_type=TransactionType.P2P, country=self.country
        )
        self.assertEqual(fee, 100)

        # Test with non-existent fee configuration
        fee = TransactionFee.get_inclusive_amount(
            transaction_type="NON_EXISTENT", country=self.country
        )
        self.assertEqual(fee, 0)


class TransactionFeeManagerTestCase(TestCase):
    def setUp(self):
        self.country1 = AvailableCountryFactory.create(name="Country1")
        self.country2 = AvailableCountryFactory.create(name="Country2")
        self.payment_method_type1 = PaymentMethodTypeFactory.create(name="Type1")
        self.payment_method_type2 = PaymentMethodTypeFactory.create(name="Type2")

        # Clear cache before each test
        cache.clear()

        # Create specific fee configurations
        self.fee1 = TransactionFee.objects.create(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type1,
            fixed_fee=None,
            percentage_fee=2.5,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

        self.fee2 = TransactionFee.objects.create(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=None,  # Default for all payment method types
            fixed_fee=None,
            percentage_fee=2.0,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

        self.fee3 = TransactionFee.objects.create(
            country=None,  # Global fee
            transaction_type=TransactionType.P2P,
            payment_method_type=None,
            fixed_fee=None,
            percentage_fee=1.5,
            fee_priority=TransactionFee.FeePriority.PERCENTAGE,
        )

    @override_settings(USE_TZ=False)  # Simplify timestamp comparison
    def test_get_applicable_fee_with_caching(self):
        """Test that get_applicable_fee uses caching for performance"""
        # First call should hit the database and cache the result
        with self.assertNumQueries(1):
            fee1 = TransactionFee.objects.get_applicable_fee(
                country=self.country1,
                transaction_type=TransactionType.P2P,
                payment_method_type=self.payment_method_type1,
            )

        # Second call with same parameters should use the cache
        with self.assertNumQueries(0):
            fee2 = TransactionFee.objects.get_applicable_fee(
                country=self.country1,
                transaction_type=TransactionType.P2P,
                payment_method_type=self.payment_method_type1,
            )

        self.assertEqual(fee1, fee2)
        self.assertEqual(
            fee1, 2.5
        )  # Now returns a single value (2.5) instead of (None, 2.5)

    def test_get_applicable_fee_specificity(self):
        """Test that get_applicable_fee returns the most specific fee configuration"""
        # Most specific: country and payment_method_type match
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type1,
        )
        self.assertEqual(
            fee, 2.5
        )  # Now returns a single value (2.5) instead of (None, 2.5)

        # Less specific: country matches, payment_method_type doesn't match any specific config
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type2,
        )
        self.assertEqual(
            fee, 2.0
        )  # Now returns a single value (2.0) instead of (None, 2.0)

        # Least specific: global fee (no country match)
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country2,  # No specific fee for country2
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type1,
        )
        self.assertEqual(
            fee, 1.5
        )  # Now returns a single value (1.5) instead of (None, 1.5)

        # Default when no matching fee is found
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type="NON_EXISTENT",
            payment_method_type=self.payment_method_type1,
        )
        self.assertEqual(fee, 0)  # Now returns a single value (0) instead of (0, 0)


class TransactionFeePerformanceTestCase(TestCase):
    def setUp(self):
        """Set up data for test methods in this class"""
        self.country = AvailableCountryFactory.create()

        # Create 5 payment method types
        self.payment_method_types = []
        for i in range(5):
            pmt = PaymentMethodTypeFactory.create()
            self.payment_method_types.append(pmt)

        # Create some transaction fees with different combinations -
        # we need to ensure no duplicates because of our unique constraint
        for i, tx_type in enumerate(
            [
                TransactionType.P2P,
                TransactionType.CashIn,
                TransactionType.CashOut,
                TransactionType.MP,
            ]
        ):
            # Use a different payment method type for each transaction type
            pmt_type = self.payment_method_types[i % 5]

            # Alternate between fixed and percentage fees
            if i % 2 == 0:
                TransactionFee.objects.create(
                    country=self.country,
                    transaction_type=tx_type,
                    payment_method_type=pmt_type,
                    fixed_fee=i * 10,
                    percentage_fee=None,
                    fee_priority=TransactionFee.FeePriority.FIXED,
                )
            else:
                TransactionFee.objects.create(
                    country=self.country,
                    transaction_type=tx_type,
                    payment_method_type=pmt_type,
                    fixed_fee=None,
                    percentage_fee=i / 10 + 1,
                    fee_priority=TransactionFee.FeePriority.PERCENTAGE,
                )

            # Also create a default fee (no payment method type)
            if i % 2 != 0:
                TransactionFee.objects.create(
                    country=self.country,
                    transaction_type=tx_type,
                    payment_method_type=None,
                    fixed_fee=i * 5,
                    percentage_fee=None,
                    fee_priority=TransactionFee.FeePriority.FIXED,
                )
            else:
                TransactionFee.objects.create(
                    country=self.country,
                    transaction_type=tx_type,
                    payment_method_type=None,
                    fixed_fee=None,
                    percentage_fee=i / 5 + 0.5,
                    fee_priority=TransactionFee.FeePriority.PERCENTAGE,
                )

        # Clear cache before the test
        cache.clear()

    def test_query_performance(self):
        """Test the performance improvements in fee lookups"""
        # Get the most specific fee (hit database)
        with self.assertNumQueries(1):
            fee1 = TransactionFee.objects.get_applicable_fee(
                country=self.country,
                transaction_type=TransactionType.P2P,
                payment_method_type=self.payment_method_types[0],
            )

        # Same query should use cache (no database hit)
        with self.assertNumQueries(0):
            fee2 = TransactionFee.objects.get_applicable_fee(
                country=self.country,
                transaction_type=TransactionType.P2P,
                payment_method_type=self.payment_method_types[0],
            )

        # Should get the same result from cache
        self.assertEqual(fee1, fee2)
