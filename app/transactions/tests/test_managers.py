from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.transactions.models import Wallet, WalletType

User = get_user_model()


class WalletManagerTestCase(TestCase):
    def setUp(self):
        # Create a test country
        self.country = AvailableCountryFactory()

        # Create test users - signal will create MAIN wallets automatically
        self.user = UserFactory(country=self.country)
        self.user_with_additional_wallet = UserFactory(country=self.country)

        # Get the automatically created main wallet
        self.main_wallet = Wallet.objects.get(
            user=self.user, wallet_type=WalletType.MAIN
        )

        # Update the balance for testing
        self.main_wallet.balance = Decimal("1000")
        self.main_wallet.save()

        # Create a business wallet for the second user
        self.business_wallet = Wallet.objects.create(
            user=self.user_with_additional_wallet,
            wallet_type=WalletType.BUSINESS,
            balance=Decimal("2000"),
        )

        # Get the main wallet for the second user
        self.second_main_wallet = Wallet.objects.get(
            user=self.user_with_additional_wallet, wallet_type=WalletType.MAIN
        )

    def test_get_user_main_wallet(self):
        """Test that get_user_main_wallet returns the user's main wallet"""
        wallet = Wallet.objects.get_user_main_wallet(self.user)
        self.assertEqual(wallet, self.main_wallet)
        self.assertEqual(wallet.wallet_type, WalletType.MAIN)
        self.assertEqual(wallet.balance, Decimal("1000"))

    def test_get_user_main_wallet_with_multiple_wallets(self):
        """Test that get_user_main_wallet returns only the main wallet when user has multiple wallets"""
        wallet = Wallet.objects.get_user_main_wallet(self.user_with_additional_wallet)
        self.assertEqual(wallet, self.second_main_wallet)
        self.assertEqual(wallet.wallet_type, WalletType.MAIN)
        self.assertNotEqual(wallet, self.business_wallet)
