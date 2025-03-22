from decimal import Decimal

from django.test import TestCase

from app.accounts.tests.factories import AvailableCountryFactory
from app.transactions.models import PlatformWallet


class PlatformWalletManagerTestCase(TestCase):
    def setUp(self):
        self.country1 = AvailableCountryFactory(
            name="Country 1", iso_code="C1", dial_code="+111", currency="USD"
        )
        self.country2 = AvailableCountryFactory(
            name="Country 2", iso_code="C2", dial_code="+222", currency="EUR"
        )

        self.platform_wallet1 = PlatformWallet.objects.create(
            balance=Decimal("1000.00"), currency="USD", country=self.country1
        )

        self.platform_wallet2 = PlatformWallet.objects.create(
            balance=Decimal("2000.00"), currency="EUR", country=self.country2
        )

        self.global_platform_wallet = PlatformWallet.objects.create(
            balance=Decimal("5000.00"), currency="USD", country=None
        )

    def test_collect_fees_with_existing_country(self):
        initial_balance = self.platform_wallet1.balance

        fee_amount = Decimal("25.50")
        PlatformWallet.objects.collect_fees(country=self.country1, amount=fee_amount)

        self.platform_wallet1.refresh_from_db()
        expected_balance = initial_balance + fee_amount
        self.assertEqual(self.platform_wallet1.balance, expected_balance)

        self.platform_wallet2.refresh_from_db()
        self.assertEqual(self.platform_wallet2.balance, Decimal("2000.00"))
        self.global_platform_wallet.refresh_from_db()
        self.assertEqual(self.global_platform_wallet.balance, Decimal("5000.00"))

    def test_collect_fees_with_non_existing_country(self):
        new_country = AvailableCountryFactory(
            name="New Country", iso_code="NC", dial_code="+333", currency="GBP"
        )

        fee_amount = Decimal("15.75")
        PlatformWallet.objects.collect_fees(country=new_country, amount=fee_amount)

        self.platform_wallet1.refresh_from_db()
        self.assertEqual(self.platform_wallet1.balance, Decimal("1000.00"))
        self.platform_wallet2.refresh_from_db()
        self.assertEqual(self.platform_wallet2.balance, Decimal("2000.00"))
        self.global_platform_wallet.refresh_from_db()
        self.assertEqual(self.global_platform_wallet.balance, Decimal("5000.00"))

    def test_collect_fees_with_none_country(self):
        initial_balance = self.global_platform_wallet.balance

        fee_amount = Decimal("30.25")
        PlatformWallet.objects.collect_fees(country=None, amount=fee_amount)

        self.global_platform_wallet.refresh_from_db()
        expected_balance = initial_balance + fee_amount
        self.assertEqual(self.global_platform_wallet.balance, expected_balance)

        self.platform_wallet1.refresh_from_db()
        self.assertEqual(self.platform_wallet1.balance, Decimal("1000.00"))
        self.platform_wallet2.refresh_from_db()
        self.assertEqual(self.platform_wallet2.balance, Decimal("2000.00"))

    def test_collect_zero_fees(self):
        initial_balance1 = self.platform_wallet1.balance

        PlatformWallet.objects.collect_fees(
            country=self.country1, amount=Decimal("0.00")
        )

        self.platform_wallet1.refresh_from_db()
        self.assertEqual(self.platform_wallet1.balance, initial_balance1)

    def test_collect_negative_fees(self):
        initial_balance1 = self.platform_wallet1.balance

        fee_amount = Decimal("-10.00")
        PlatformWallet.objects.collect_fees(country=self.country1, amount=fee_amount)

        self.platform_wallet1.refresh_from_db()
        expected_balance = initial_balance1 + fee_amount
        self.assertEqual(self.platform_wallet1.balance, expected_balance)

    def test_collect_fees_multiple_times(self):
        initial_balance = self.platform_wallet1.balance

        fee_amounts = [Decimal("5.25"), Decimal("10.50"), Decimal("15.75")]
        total_fees = sum(fee_amounts)

        for fee in fee_amounts:
            PlatformWallet.objects.collect_fees(country=self.country1, amount=fee)

        self.platform_wallet1.refresh_from_db()
        expected_balance = initial_balance + total_fees
        self.assertEqual(self.platform_wallet1.balance, expected_balance)
