from django.test import TestCase

from app.accounts.tests.factories import UserFactory
from app.transactions.models import Wallet, WalletType


class WalletSignalTestCase(TestCase):
    def test_main_wallet_creation_on_user_creation(self):
        user = UserFactory.create()

        self.assertTrue(
            Wallet.objects.filter(user=user, wallet_type=WalletType.MAIN).exists()
        )

        wallet = Wallet.objects.get(user=user, wallet_type=WalletType.MAIN)
        self.assertEqual(wallet.balance, 0)
        self.assertTrue(wallet.is_active)

    def test_no_duplicate_main_wallet_creation(self):
        user = UserFactory.create()

        self.assertTrue(
            Wallet.objects.filter(user=user, wallet_type=WalletType.MAIN).exists()
        )

        initial_count = Wallet.objects.filter(user=user).count()

        user.save()

        self.assertEqual(Wallet.objects.filter(user=user).count(), initial_count)
