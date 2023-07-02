from django.test import SimpleTestCase

from app.transactions.utils import compute_inclusive_amount


class ComputeInclusiveAmountTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()

    def test_it_should_compute_inclusive_amount(self):
        amount, fee = 1000, 2
        expected_charged_amount, expected_calculated_fee = float(1020), float(20)

        inclusive_amount = compute_inclusive_amount(amount=amount, applicable_fee=fee)
        calculated_fee, charged_amount = inclusive_amount

        self.assertIsInstance(inclusive_amount, tuple)
        self.assertEqual(charged_amount, expected_charged_amount)
        self.assertEqual(calculated_fee, expected_calculated_fee)
