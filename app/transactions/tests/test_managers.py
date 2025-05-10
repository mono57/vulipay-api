from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.transactions.models import Wallet, WalletType

User = get_user_model()


class WalletManagerTestCase(TestCase):
    def setUp(self):
        # Create a test country
        self.country = AvailableCountryFactory.create()

        # Create test users
        self.user = UserFactory(country=self.country)
        self.user_with_additional_wallet = UserFactory(country=self.country)

        # Create main wallet explicitly since it's no longer created automatically by a signal
        self.main_wallet = Wallet.objects.create(
            user=self.user, wallet_type=WalletType.MAIN, balance=Decimal("1000")
        )

        # Create main wallet for the second user
        self.second_main_wallet = Wallet.objects.create(
            user=self.user_with_additional_wallet, wallet_type=WalletType.MAIN
        )

        # Create a business wallet for the second user
        self.business_wallet = Wallet.objects.create(
            user=self.user_with_additional_wallet,
            wallet_type=WalletType.BUSINESS,
            balance=Decimal("2000"),
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

    def test_get_wallet_with_valid_id(self):
        """Test that get_wallet returns the wallet when given a valid wallet ID and user"""
        wallet = Wallet.objects.get_wallet(self.main_wallet.id, self.user)
        self.assertEqual(wallet, self.main_wallet)
        self.assertEqual(wallet.wallet_type, WalletType.MAIN)

    def test_get_wallet_with_multiple_wallet_types(self):
        """Test that get_wallet returns the correct wallet type"""
        # Get main wallet
        main_wallet = Wallet.objects.get_wallet(
            self.second_main_wallet.id, self.user_with_additional_wallet
        )
        self.assertEqual(main_wallet, self.second_main_wallet)
        self.assertEqual(main_wallet.wallet_type, WalletType.MAIN)

        # Get business wallet
        business_wallet = Wallet.objects.get_wallet(
            self.business_wallet.id, self.user_with_additional_wallet
        )
        self.assertEqual(business_wallet, self.business_wallet)
        self.assertEqual(business_wallet.wallet_type, WalletType.BUSINESS)

    def test_get_wallet_with_invalid_id(self):
        """Test that get_wallet returns None when given an invalid wallet ID"""
        wallet = Wallet.objects.get_wallet(999999, self.user)
        self.assertIsNone(wallet)

    def test_get_wallet_belonging_to_different_user(self):
        """Test that get_wallet returns None when the wallet belongs to a different user"""
        wallet = Wallet.objects.get_wallet(
            self.main_wallet.id, self.user_with_additional_wallet
        )
        self.assertIsNone(wallet)
