from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings

from app.accounts.tests.factories import AvailableCountryFactory
from app.transactions.models import PaymentMethodType, TransactionFee, TransactionType
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


class TransactionAllowedTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()

        # Create payment method types with different allowed transactions
        self.pmt_all_allowed = PaymentMethodType.objects.create(
            name="All Transactions Allowed",
            code="ALL_ALLOWED",
            country=self.country,
            allowed_transactions=None,  # None means all are allowed
        )

        self.pmt_specific_allowed = PaymentMethodType.objects.create(
            name="Specific Transactions Allowed",
            code="SPECIFIC",
            country=self.country,
            allowed_transactions=[TransactionType.P2P, TransactionType.CashIn],
        )

        self.pmt_none_allowed = PaymentMethodType.objects.create(
            name="No Transactions Allowed",
            code="NONE_ALLOWED",
            country=self.country,
            allowed_transactions=[],  # Empty list means none are allowed
        )

    def test_transaction_allowed_with_none_pmt(self):
        """Test that transactions are allowed when no payment method type is provided"""
        # With the new implementation, this should be false for all types when no payment method type is provided
        self.assertFalse(PaymentMethodType.is_transaction_allowed(TransactionType.P2P))
        self.assertFalse(PaymentMethodType.is_transaction_allowed(TransactionType.MP))
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(TransactionType.CashIn)
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(TransactionType.CashOut)
        )

    def test_transaction_allowed_with_all_allowed_pmt(self):
        """Test that all transactions are allowed with payment method type that allows all"""
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.P2P, payment_method_type_id=self.pmt_all_allowed.id
            )
        )
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.MP, payment_method_type_id=self.pmt_all_allowed.id
            )
        )
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashIn, payment_method_type_id=self.pmt_all_allowed.id
            )
        )
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashOut, payment_method_type_id=self.pmt_all_allowed.id
            )
        )

    def test_transaction_allowed_with_specific_allowed_pmt(self):
        """Test that only specific transactions are allowed with payment method type that allows specific types"""
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.P2P, payment_method_type_id=self.pmt_specific_allowed.id
            )
        )
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashIn,
                payment_method_type_id=self.pmt_specific_allowed.id,
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.MP, payment_method_type_id=self.pmt_specific_allowed.id
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashOut,
                payment_method_type_id=self.pmt_specific_allowed.id,
            )
        )

    def test_transaction_allowed_with_none_allowed_pmt(self):
        """Test that no transactions are allowed with payment method type that allows none"""
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.P2P, payment_method_type_id=self.pmt_none_allowed.id
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.MP, payment_method_type_id=self.pmt_none_allowed.id
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashIn, payment_method_type_id=self.pmt_none_allowed.id
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.CashOut, payment_method_type_id=self.pmt_none_allowed.id
            )
        )

    def test_transaction_allowed_with_payment_method_type_id(self):
        """Test that the method works when using payment_method_type_id instead of the object"""
        self.assertTrue(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.P2P, payment_method_type_id=self.pmt_specific_allowed.id
            )
        )
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.MP, payment_method_type_id=self.pmt_specific_allowed.id
            )
        )

    def test_transaction_allowed_with_nonexistent_payment_method_type_id(self):
        """Test that transactions are not allowed when the payment method type doesn't exist"""
        self.assertFalse(
            PaymentMethodType.is_transaction_allowed(
                TransactionType.P2P, payment_method_type_id=999999
            )
        )


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

    def test_get_applicable_fee_with_payment_method_type_id(self):
        """Test that get_applicable_fee works correctly with payment_method_type_id parameter"""
        # Clear cache before the test
        cache.clear()

        # Test with payment_method_type_id
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type_id=self.payment_method_type1.id,
        )
        self.assertEqual(fee, 2.5)

        # Test with payment_method_type object (should give same result)
        fee2 = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type1,
        )
        self.assertEqual(fee, fee2)

        # Test with both parameters (payment_method_type_id should take precedence)
        fee3 = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type=self.payment_method_type2,
            payment_method_type_id=self.payment_method_type1.id,
        )
        self.assertEqual(
            fee3, 2.5
        )  # Should use payment_method_type1, not payment_method_type2

    def test_get_applicable_fee_with_direct_id_values(self):
        """Test that get_applicable_fee works correctly with direct ID values"""
        # Clear cache before the test
        cache.clear()

        # Test with country_id and payment_method_type_id
        fee = TransactionFee.objects.get_applicable_fee(
            country=self.country1.id,
            transaction_type=TransactionType.P2P,
            payment_method_type_id=self.payment_method_type1.id,
        )
        self.assertEqual(fee, 2.5)

        # Test with country object and payment_method_type_id
        fee2 = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type_id=self.payment_method_type1.id,
        )
        self.assertEqual(fee, fee2)

        # Test non-existent payment_method_type_id should fallback to default
        fee3 = TransactionFee.objects.get_applicable_fee(
            country=self.country1,
            transaction_type=TransactionType.P2P,
            payment_method_type_id=9999,  # Non-existent ID
        )
        self.assertEqual(fee3, 2.0)  # Should use the country-specific default


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
