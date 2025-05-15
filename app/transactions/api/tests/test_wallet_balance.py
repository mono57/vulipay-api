from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from app.transactions.models import Wallet, WalletType

User = get_user_model()


class WalletBalanceAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test_wallet_balance@example.com",
            password="testpassword123",
            full_name="Test User",
        )

        self.main_wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("500.00"),
            wallet_type=WalletType.MAIN,
            currency="USD",
        )

        self.business_wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("1000.00"),
            wallet_type=WalletType.BUSINESS,
            currency="USD",
        )

        self.url = reverse("api:transactions:wallet-balance")
        self.client.force_authenticate(user=self.user)

    def test_get_main_wallet_balance_explicit(self):
        response = self.client.get(f"{self.url}?wallet_type={WalletType.MAIN}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), self.main_wallet.balance)

    def test_get_main_wallet_balance_default(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), self.main_wallet.balance)

    def test_get_business_wallet_balance(self):
        response = self.client.get(f"{self.url}?wallet_type={WalletType.BUSINESS}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data["balance"]), self.business_wallet.balance
        )

    def test_get_nonexistent_wallet_type(self):
        response = self.client.get(f"{self.url}?wallet_type=NONEXISTENT")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
