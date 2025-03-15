import json
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app.accounts.tests.factories import UserFactory
from app.core.utils.encryption import decrypt_data
from app.transactions.models import Wallet, WalletType


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

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
