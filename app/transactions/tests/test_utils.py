from django.test import SimpleTestCase

from app.transactions.models import TransactionFee
from app.transactions.utils import compute_inclusive_amount


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
