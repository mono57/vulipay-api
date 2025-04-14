import json
from decimal import Decimal
from unittest.mock import patch

from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.models import AvailableCountry, User
from app.accounts.tests.factories import UserFactory
from app.core.utils.encryption import decrypt_data, encrypt_data
from app.transactions.models import TransactionType, Wallet, WalletType


class ReceiveFundsPaymentCodeAPIViewTestCase(APITestCase):
    def setUp(self):
        self.country = AvailableCountry.objects.create(
            name="Test Country",
            dial_code="999",
            iso_code="TST",
            phone_number_regex=r"^\+999\d{8}$",
            currency="XAF",
        )

        self.user = UserFactory.create(
            email="test@example.com",
            phone_number="+237612345678",
            full_name="Test User",
            country=self.country,
        )

        # Delete any existing wallets for this user
        Wallet.objects.filter(user=self.user).delete()

        # Create a wallet manually
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_type=WalletType.MAIN,
            balance=Decimal("1000.00"),
            currency="XAF",
            is_active=True,
        )

        self.url = reverse("api:transactions:receive-funds-payment-code")
        self.client.force_authenticate(user=self.user)

    def test_get_payment_code_without_amount(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["target_wallet_id"], self.wallet.id)
        self.assertEqual(decrypted_data["transaction_type"], TransactionType.P2P)
        self.assertEqual(decrypted_data["target_wallet_currency"], "XAF")
        self.assertNotIn("amount", decrypted_data)

    def test_get_payment_code_with_amount(self):
        amount = 500.50
        response = self.client.post(self.url, {"amount": amount}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["target_wallet_id"], self.wallet.id)
        self.assertEqual(decrypted_data["transaction_type"], TransactionType.P2P)
        self.assertEqual(decrypted_data["target_wallet_currency"], "XAF")
        self.assertEqual(decrypted_data["amount"], float(amount))

    def test_invalid_amount_format(self):
        response = self.client.post(self.url, {"amount": "invalid"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDataDecryptionAPIViewTestCase(APITestCase):
    def setUp(self):
        # Create a country with currency
        self.country = AvailableCountry.objects.create(
            name="Test Country",
            dial_code="999",
            iso_code="TST",
            phone_number_regex=r"^\+999\d{8}$",
            currency="XAF",
        )

        # Create a user with this country
        self.user = UserFactory.create(
            email="test@example.com",
            phone_number="+237612345678",
            full_name="Test User",
            country=self.country,
        )

        # Delete any existing wallets for this user
        Wallet.objects.filter(user=self.user).delete()

        # Create a wallet manually
        self.wallet = Wallet.objects.create(
            user=self.user,
            wallet_type=WalletType.MAIN,
            balance=Decimal("1000.00"),
            currency="XAF",
            is_active=True,
        )

        self.url = reverse("api:transactions:decrypt-user-data")
        self.client.force_authenticate(user=self.user)

    def test_decrypt_user_data_without_amount(self):
        # Create test data
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "target_wallet_id": self.wallet.id,
            "transaction_type": TransactionType.P2P,
            "target_wallet_currency": "XAF",
        }
        encrypted_data = encrypt_data(data)

        # Test decryption
        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["phone_number"], self.user.phone_number)
        self.assertEqual(response.data["target_wallet_id"], self.wallet.id)
        self.assertEqual(response.data["transaction_type"], TransactionType.P2P)
        self.assertEqual(response.data["target_wallet_currency"], "XAF")
        self.assertNotIn("amount", response.data)

    def test_decrypt_user_data_with_amount(self):
        amount = 500.50
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "target_wallet_id": self.wallet.id,
            "transaction_type": TransactionType.P2P,
            "target_wallet_currency": "XAF",
            "amount": float(amount),
        }
        encrypted_data = encrypt_data(data)

        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["phone_number"], self.user.phone_number)
        self.assertEqual(response.data["target_wallet_id"], self.wallet.id)
        self.assertEqual(response.data["transaction_type"], TransactionType.P2P)
        self.assertEqual(response.data["target_wallet_currency"], "XAF")
        self.assertEqual(response.data["amount"], float(amount))

    def test_invalid_encrypted_data(self):
        response = self.client.post(
            self.url, {"encrypted_data": "invalid_data"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_authentication_required(self):
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "target_wallet_id": self.wallet.id,
            "transaction_type": TransactionType.P2P,
            "target_wallet_currency": "XAF",
        }
        encrypted_data = encrypt_data(data)

        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
