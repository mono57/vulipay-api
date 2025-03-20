from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.transactions.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)


class ProcessTransactionAPIViewTestCase(APITestCase):
    def setUp(self):
        # Create countries with currencies
        self.country = AvailableCountryFactory(
            name="Test Country", dial_code="123", iso_code="TC", currency="USD"
        )
        self.other_country = AvailableCountryFactory(
            name="Other Country", dial_code="456", iso_code="OC", currency="EUR"
        )

        # Create users with PINs
        self.sender = UserFactory(country=self.country)
        self.sender.set_pin("1234")
        self.sender.save()

        self.recipient = UserFactory(country=self.country)

        # Create wallets for users
        self.sender_wallet = Wallet.objects.get(
            user=self.sender, wallet_type=WalletType.MAIN
        )
        self.sender_wallet.deposit(1000)  # Add funds to sender's wallet

        self.recipient_wallet = Wallet.objects.get(
            user=self.recipient, wallet_type=WalletType.MAIN
        )

        # URL for the endpoint
        self.url = reverse("api:transactions:process-transaction")

        # Authentication token
        self.token = RefreshToken.for_user(self.sender).access_token

    def test_process_transaction_success(self):
        """Test successful transaction processing with correct PIN."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Initial balance check
        sender_initial_balance = self.sender_wallet.balance
        recipient_initial_balance = self.recipient_wallet.balance

        # Prepare transaction data with valid PIN
        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "phone_number": self.recipient.phone_number,
            "currency": "USD",
            "pin": "1234",
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], "USD")
        self.assertEqual(response.data["amount"], 100.0)
        self.assertEqual(response.data["status"], TransactionStatus.COMPLETED)

        # Verify balances have been updated
        self.sender_wallet.refresh_from_db()
        self.recipient_wallet.refresh_from_db()

        self.assertEqual(
            self.sender_wallet.balance, sender_initial_balance - Decimal("100")
        )
        self.assertEqual(
            self.recipient_wallet.balance, recipient_initial_balance + Decimal("100")
        )

        # Verify transaction was created
        transaction = Transaction.objects.latest("id")
        self.assertEqual(transaction.status, TransactionStatus.COMPLETED)
        self.assertEqual(transaction.amount, Decimal("100"))
        self.assertEqual(transaction.type, TransactionType.P2P)

    def test_invalid_pin(self):
        """Test that transaction fails with invalid PIN."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Prepare transaction data with invalid PIN
        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "currency": "USD",
            "pin": "9999",  # Wrong PIN
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify balances have not changed
        self.sender_wallet.refresh_from_db()
        self.recipient_wallet.refresh_from_db()

        self.assertEqual(self.sender_wallet.balance, Decimal("1000"))
        self.assertEqual(self.recipient_wallet.balance, Decimal("0"))

    def test_missing_pin(self):
        """Test that transaction fails with missing PIN."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Prepare transaction data without PIN
        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "currency": "USD",
            # Missing PIN
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_currency_mismatch(self):
        """Test that transaction fails when currency doesn't match user's currency."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Prepare transaction data with wrong currency
        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "currency": "EUR",  # User's currency is USD
            "pin": "1234",
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency", response.data)

    def test_insufficient_funds(self):
        """Test that transaction fails when user has insufficient funds."""
        # Set sender wallet balance to a small amount
        self.sender_wallet.balance = 50
        self.sender_wallet.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "phone_number": self.recipient.phone_number,
            "currency": "USD",
            "pin": "1234",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if there's any error message containing 'insufficient funds'
        error_found = False
        for error in response.data.get("detail", []):
            if "insufficient funds" in str(error).lower():
                error_found = True
                break

        self.assertTrue(error_found, "No error message about insufficient funds found")

    def test_serializer_validation_no_source_wallet(self):
        """Test that the serializer validates source wallet existence."""
        # Delete the sender's main wallet
        Wallet.objects.filter(user=self.sender, wallet_type=WalletType.MAIN).delete()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": "John Doe",
            "email": "johndoe@example.com",
            "phone_number": "1234567890",
            "currency": "USD",
            "pin": "1234",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if there's any error message containing 'source wallet'
        error_found = False
        for error in response.data.get("detail", []):
            if "source wallet" in str(error).lower():
                error_found = True
                break

        self.assertTrue(error_found, "No error message about source wallet found")

    def test_serializer_validation_insufficient_funds(self):
        """Test that the serializer validates sufficient funds."""
        # Set sender wallet balance to a low amount
        self.sender_wallet.balance = 50
        self.sender_wallet.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": "John Doe",
            "email": "johndoe@example.com",
            "phone_number": "1234567890",
            "currency": "USD",
            "pin": "1234",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if there's any error message containing 'insufficient funds'
        error_found = False
        for error in response.data.get("detail", []):
            if "insufficient funds" in str(error).lower():
                error_found = True
                break

        self.assertTrue(error_found, "No error message about insufficient funds found")
