import json
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.tests.factories import UserFactory
from app.core.utils.encryption import decrypt_data, encrypt_data
from app.transactions.models import TransactionType, Wallet, WalletType


class UserDataEncryptionAPIViewTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory.create(
            email="test@example.com",
            phone_number="+237612345678",
            full_name="Test User",
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user,
            wallet_type=WalletType.MAIN,
            defaults={"balance": Decimal("1000.00")},
        )
        self.url = reverse("api:transactions:encrypt-user-data")
        self.client.force_authenticate(user=self.user)

    def test_encrypt_user_data_without_amount(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["wallet_id"], self.wallet.id)
        self.assertNotIn("amount", decrypted_data)
        self.assertNotIn("transaction_type", decrypted_data)

    def test_encrypt_user_data_with_amount(self):
        amount = 500.50
        response = self.client.post(self.url, {"amount": amount}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["wallet_id"], self.wallet.id)
        self.assertEqual(decrypted_data["amount"], float(amount))
        self.assertNotIn("transaction_type", decrypted_data)

    def test_encrypt_user_data_with_transaction_type(self):
        transaction_type = TransactionType.P2P
        response = self.client.post(
            self.url, {"transaction_type": transaction_type}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["wallet_id"], self.wallet.id)
        self.assertNotIn("amount", decrypted_data)
        self.assertEqual(decrypted_data["transaction_type"], transaction_type)

    def test_encrypt_user_data_with_amount_and_transaction_type(self):
        amount = 500.50
        transaction_type = TransactionType.P2P
        response = self.client.post(
            self.url,
            {"amount": amount, "transaction_type": transaction_type},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("encrypted_data", response.data)

        encrypted_data = response.data["encrypted_data"]
        decrypted_data = decrypt_data(encrypted_data)

        self.assertEqual(decrypted_data["full_name"], self.user.full_name)
        self.assertEqual(decrypted_data["email"], self.user.email)
        self.assertEqual(decrypted_data["phone_number"], self.user.phone_number)
        self.assertEqual(decrypted_data["wallet_id"], self.wallet.id)
        self.assertEqual(decrypted_data["amount"], float(amount))
        self.assertEqual(decrypted_data["transaction_type"], transaction_type)

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDataDecryptionAPIViewTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory.create(
            email="test@example.com",
            phone_number="+237612345678",
            full_name="Test User",
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user,
            wallet_type=WalletType.MAIN,
            defaults={"balance": Decimal("1000.00")},
        )
        self.url = reverse("api:transactions:decrypt-user-data")
        self.client.force_authenticate(user=self.user)

    def test_decrypt_user_data_without_amount(self):
        # Create test data
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "wallet_id": self.wallet.id,
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
        self.assertEqual(response.data["wallet_id"], self.wallet.id)
        self.assertNotIn("amount", response.data)
        self.assertNotIn("transaction_type", response.data)

    def test_decrypt_user_data_with_amount(self):
        amount = 500.50
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "wallet_id": self.wallet.id,
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
        self.assertEqual(response.data["wallet_id"], self.wallet.id)
        self.assertEqual(response.data["amount"], float(amount))
        self.assertNotIn("transaction_type", response.data)

    def test_decrypt_user_data_with_transaction_type(self):
        transaction_type = TransactionType.P2P
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "wallet_id": self.wallet.id,
            "transaction_type": transaction_type,
        }
        encrypted_data = encrypt_data(data)

        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["phone_number"], self.user.phone_number)
        self.assertEqual(response.data["wallet_id"], self.wallet.id)
        self.assertNotIn("amount", response.data)
        self.assertEqual(response.data["transaction_type"], transaction_type)

    def test_decrypt_user_data_with_amount_and_transaction_type(self):
        amount = 500.50
        transaction_type = TransactionType.P2P
        data = {
            "full_name": self.user.full_name,
            "email": self.user.email,
            "phone_number": self.user.phone_number,
            "wallet_id": self.wallet.id,
            "amount": float(amount),
            "transaction_type": transaction_type,
        }
        encrypted_data = encrypt_data(data)

        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["phone_number"], self.user.phone_number)
        self.assertEqual(response.data["wallet_id"], self.wallet.id)
        self.assertEqual(response.data["amount"], float(amount))
        self.assertEqual(response.data["transaction_type"], transaction_type)

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
            "wallet_id": self.wallet.id,
        }
        encrypted_data = encrypt_data(data)

        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, {"encrypted_data": encrypted_data}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
