from django.test import SimpleTestCase

from app.transactions.models import TransactionFee
from app.transactions.utils import compute_inclusive_amount, process_fee_dict


class ComputeInclusiveAmountTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()

    def test_it_should_compute_inclusive_amount_percentage(self):
        amount, fee = 1000, 2
        expected_charged_amount, expected_calculated_fee = float(1020), float(20)

        inclusive_amount = compute_inclusive_amount(
            amount=amount,
            applicable_fee=fee,
            fee_type=TransactionFee.FeePriority.PERCENTAGE,
        )
        calculated_fee, charged_amount = inclusive_amount

        self.assertIsInstance(inclusive_amount, tuple)
        self.assertEqual(charged_amount, expected_charged_amount)
        self.assertEqual(calculated_fee, expected_calculated_fee)

    def test_it_should_compute_inclusive_amount_fixed(self):
        amount, fee = 1000, 2
        expected_charged_amount, expected_calculated_fee = float(1002), float(2)

        inclusive_amount = compute_inclusive_amount(
            amount=amount, applicable_fee=fee, fee_type=TransactionFee.FeePriority.FIXED
        )
        calculated_fee, charged_amount = inclusive_amount

        self.assertIsInstance(inclusive_amount, tuple)
        self.assertEqual(charged_amount, expected_charged_amount)
        self.assertEqual(calculated_fee, expected_calculated_fee)

    def test_it_should_detect_fee_type_automatically(self):
        # Test with small value (likely a percentage)
        amount, fee = 1000, 2.5
        inclusive_amount = compute_inclusive_amount(amount=amount, applicable_fee=fee)
        calculated_fee, charged_amount = inclusive_amount

        # Should be treated as percentage (2.5%)
        expected_fee = (1000 * 2.5) / 100  # 25.0
        self.assertEqual(calculated_fee, expected_fee)
        self.assertEqual(charged_amount, amount + expected_fee)

        # Test with large value (likely a fixed fee)
        amount, fee = 1000, 200
        inclusive_amount = compute_inclusive_amount(amount=amount, applicable_fee=fee)
        calculated_fee, charged_amount = inclusive_amount

        # Should be treated as fixed fee ($200)
        self.assertEqual(calculated_fee, 200)
        self.assertEqual(charged_amount, 1200)


class ProcessFeeDictTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()

    def test_process_fee_dict_with_percentage_fee(self):
        amount = 1000
        fee_dict = {"fee_value": 2.5, "fee_type": TransactionFee.FeePriority.PERCENTAGE}

        result = process_fee_dict(amount, fee_dict)
        calculated_fee, charged_amount = result

        self.assertIsInstance(result, tuple)
        self.assertEqual(float(calculated_fee), 25.0)
        self.assertEqual(float(charged_amount), 1025.0)

    def test_process_fee_dict_with_fixed_fee(self):
        amount = 1000
        fee_dict = {"fee_value": 50, "fee_type": TransactionFee.FeePriority.FIXED}

        result = process_fee_dict(amount, fee_dict)
        calculated_fee, charged_amount = result

        self.assertIsInstance(result, tuple)
        self.assertEqual(float(calculated_fee), 50.0)
        self.assertEqual(float(charged_amount), 1050.0)

    def test_process_fee_dict_with_percentage_as_default(self):
        amount = 1000
        fee_dict = {
            "fee_value": 3.5
            # No fee_type provided
        }

        result = process_fee_dict(amount, fee_dict)
        calculated_fee, charged_amount = result

        # Should always treat as percentage when fee_type is not specified
        self.assertEqual(float(calculated_fee), 35.0)
        self.assertEqual(float(charged_amount), 1035.0)

    def test_process_fee_dict_with_large_value_as_percentage(self):
        amount = 1000
        fee_dict = {
            "fee_value": 150
            # No fee_type provided
        }

        result = process_fee_dict(amount, fee_dict)
        calculated_fee, charged_amount = result

        # Should always treat as percentage when fee_type is not specified
        self.assertEqual(float(calculated_fee), 1500.0)
        self.assertEqual(float(charged_amount), 2500.0)

    def test_process_fee_dict_with_decimal_input(self):
        from decimal import Decimal

        amount = Decimal("1000.00")
        fee_dict = {
            "fee_value": Decimal("2.50"),
            "fee_type": TransactionFee.FeePriority.PERCENTAGE,
        }

        result = process_fee_dict(amount, fee_dict)
        calculated_fee, charged_amount = result

        self.assertEqual(calculated_fee, Decimal("25.00"))
        self.assertEqual(charged_amount, Decimal("1025.00"))

    def test_process_fee_dict_with_none_or_empty_dict(self):
        amount = 1000

        # Test with None
        result1 = process_fee_dict(amount, None)
        calculated_fee1, charged_amount1 = result1

        self.assertEqual(float(calculated_fee1), 0.0)
        self.assertEqual(float(charged_amount1), 1000.0)

        # Test with empty dict
        result2 = process_fee_dict(amount, {})
        calculated_fee2, charged_amount2 = result2

        self.assertEqual(float(calculated_fee2), 0.0)
        self.assertEqual(float(charged_amount2), 1000.0)
