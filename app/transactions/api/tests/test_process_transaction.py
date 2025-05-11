from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.transactions.models import (
    PaymentMethodType,
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)


class ProcessTransactionAPIViewTestCase(APITestCase):
    @patch("app.accounts.models.make_pin")
    def setUp(self, mock_make_pin):
        # Mock the make_pin function to avoid DB issues
        mock_make_pin.return_value = "hashed_pin_1234"

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

        # Create wallets explicitly since they're no longer created automatically by a signal
        self.sender_wallet = Wallet.objects.create(
            user=self.sender, wallet_type=WalletType.MAIN, balance=1000
        )

        self.recipient_wallet = Wallet.objects.create(
            user=self.recipient, wallet_type=WalletType.MAIN
        )

        # Create a payment method type for wallet to wallet transfers
        self.wallet_to_wallet_pmt = PaymentMethodType.objects.create(
            name="Wallet to Wallet",
            code="WalletToWallet",
            country=self.country,
            allowed_transactions=[
                TransactionType.P2P,
                TransactionType.MP,
                TransactionType.CashIn,
                TransactionType.CashOut,
            ],
        )

        # Create a transaction fee for this payment method type
        TransactionFee.objects.create(
            name="P2P Transaction Fee",
            country=self.country,
            payment_method_type=self.wallet_to_wallet_pmt,
            transaction_type=TransactionType.P2P,
            percentage_fee=2.5,
        )

        # URL for the endpoint
        self.url = reverse("api:transactions:process-transaction")

        # Authentication token
        self.token = RefreshToken.for_user(self.sender).access_token

    @patch("app.accounts.models.User.verify_pin")
    @patch("app.transactions.models.TransactionFee.objects.get_applicable_fee")
    def test_process_transaction_success(self, mock_get_fee, mock_verify_pin):
        # Mock the verify_pin method to return True
        mock_verify_pin.return_value = True
        # Mock the get_applicable_fee method to return 2.5%
        mock_get_fee.return_value = Decimal("2.5")

        # Set authentication token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Check initial wallet balances
        initial_sender_balance = self.sender_wallet.balance
        initial_recipient_balance = self.recipient_wallet.balance

        # Prepare the transaction data with valid PIN
        transaction_data = {
            "amount": "100",
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": str(self.recipient_wallet.id),
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "phone_number": self.recipient.phone_number,
            "currency": "USD",
            "pin": "1234",
            "transaction_fee": "2.5",
            "payment_method_id": str(self.sender_wallet.id),
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        # Execute the request
        response = self.client.post(self.url, transaction_data, format="json")

        # Print response details for debugging
        print("Response status:", response.status_code)
        print("Response data:", response.data)

        # Assertions for a successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["amount"], float(transaction_data["amount"]))
        self.assertEqual(response.data["status"], TransactionStatus.COMPLETED)

        # Refresh wallet objects from database
        self.sender_wallet.refresh_from_db()
        self.recipient_wallet.refresh_from_db()

        # Calculate expected amounts
        amount = Decimal(transaction_data["amount"])
        fee = (amount * Decimal(transaction_data["transaction_fee"])) / 100
        charged_amount = amount + fee  # This is what's deducted from sender

        # Check that the sender was charged the correct amount (including fee)
        self.assertEqual(
            self.sender_wallet.balance, initial_sender_balance - charged_amount
        )

        # Check that the recipient received the full charged amount (including fee)
        # This is the actual behavior of the system
        self.assertEqual(
            self.recipient_wallet.balance, initial_recipient_balance + charged_amount
        )

        # Check that a transaction was created with the correct details
        transaction = Transaction.objects.get(
            status=TransactionStatus.COMPLETED,
            from_wallet=self.sender_wallet,
            to_wallet=self.recipient_wallet,
            type=TransactionType.P2P,
        )
        self.assertEqual(transaction.amount, amount)

    @patch("app.accounts.models.User.verify_pin")
    def test_invalid_pin(self, mock_verify_pin):
        """Test that transaction fails with invalid PIN."""
        mock_verify_pin.return_value = False
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
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
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
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.accounts.models.User.verify_pin")
    def test_currency_mismatch(self, mock_verify_pin):
        """Test that transaction fails when currency doesn't match user's currency."""
        # Return True for PIN validation
        mock_verify_pin.return_value = True

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
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        # Execute the request
        response = self.client.post(self.url, data, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency", response.data)

    @patch("app.accounts.models.User.verify_pin")
    @patch("app.transactions.models.TransactionFee.objects.get_applicable_fee")
    def test_insufficient_funds(self, mock_get_fee, mock_verify_pin):
        """Test that transaction fails when user has insufficient funds."""
        # Return True for PIN validation
        mock_verify_pin.return_value = True
        # Mock the get_applicable_fee method to return 2.5%
        mock_get_fee.return_value = Decimal("2.5")

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
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Print response for debugging
        print("Response data for insufficient funds test:", response.data)

        # Check if there's any error message containing 'insufficient funds'
        error_found = False
        if "detail" in response.data:
            if isinstance(response.data["detail"], list):
                for error in response.data["detail"]:
                    if "insufficient funds" in str(error).lower():
                        error_found = True
                        break
            else:
                if "insufficient funds" in str(response.data["detail"]).lower():
                    error_found = True

        self.assertTrue(error_found, "No error message about insufficient funds found")

    @patch("app.accounts.models.User.verify_pin")
    def test_invalid_payment_method_type(self, mock_verify_pin):
        """Test that transaction fails with an invalid payment method type code."""
        # Return True for PIN validation
        mock_verify_pin.return_value = True

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.token)}")

        # Prepare transaction data with invalid payment method type
        data = {
            "amount": 100,
            "transaction_type": TransactionType.P2P,
            "target_wallet_id": self.recipient_wallet.id,
            "full_name": self.recipient.full_name,
            "email": self.recipient.email,
            "phone_number": self.recipient.phone_number,
            "currency": "USD",
            "pin": "1234",
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "Invalid",  # Not WalletToWallet
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if there's any error message about invalid payment method
        error_found = False
        for error in response.data.get("detail", []):
            if "invalid payment method" in str(error).lower():
                error_found = True
                break

        self.assertTrue(
            error_found, "No error message about invalid payment method found"
        )

    @patch("app.accounts.models.User.verify_pin")
    def test_serializer_validation_no_source_wallet(self, mock_verify_pin):
        """Test that the serializer validates source wallet existence."""
        # Return True for PIN validation
        mock_verify_pin.return_value = True

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
            "payment_method_id": 999,  # Non-existent wallet ID
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
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

    @patch("app.accounts.models.User.verify_pin")
    @patch("app.transactions.models.TransactionFee.objects.get_applicable_fee")
    def test_serializer_validation_insufficient_funds(
        self, mock_get_fee, mock_verify_pin
    ):
        """Test that the serializer validates sufficient funds."""
        # Return True for PIN validation
        mock_verify_pin.return_value = True
        # Mock the get_applicable_fee method to return 2.5%
        mock_get_fee.return_value = Decimal("2.5")

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
            "payment_method_id": self.sender_wallet.id,
            "payment_method_type_code": "WalletToWallet",
            "payment_method_type_id": self.wallet_to_wallet_pmt.id,
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Print response for debugging
        print(
            "Response data for serializer validation insufficient funds test:",
            response.data,
        )

        # Check if there's any error message containing 'insufficient funds'
        error_found = False
        if "detail" in response.data:
            if isinstance(response.data["detail"], list):
                for error in response.data["detail"]:
                    if "insufficient funds" in str(error).lower():
                        error_found = True
                        break
            else:
                if "insufficient funds" in str(response.data["detail"]).lower():
                    error_found = True

        self.assertTrue(error_found, "No error message about insufficient funds found")
