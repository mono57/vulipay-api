import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.tests import factories as f
from app.accounts.tests.factories import AvailableCountryFactory, UserFactory
from app.core.utils import make_payment_code, make_transaction_ref
from app.transactions.models import (
    PaymentMethod,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)
from app.transactions.tests.factories import PaymentMethodTypeFactory


class PaymentMethodAPITestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.country = AvailableCountryFactory.create(name="Cameroon", iso_code="CM")

        # Create payment method types with specific transaction fees
        self.visa_type = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Visa",
            country=self.country,
            cash_in_transaction_fee=1.5,
            cash_out_transaction_fee=2.0,
        )
        self.mtn_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="MTN Mobile Money",
                country=self.country,
                cash_in_transaction_fee=0.5,
                cash_out_transaction_fee=1.0,
            )
        )

        # Create payment methods with associated payment method types
        self.card_payment = PaymentMethod.objects.create(
            user=self.user,
            type="card",
            cardholder_name="John Doe",
            masked_card_number="**** **** **** 1234",
            expiry_date="12/2025",
            cvv_hash="hashed_cvv",
            billing_address="123 Main St, City, Country",
            default_method=True,
        )

        self.mobile_payment = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN Mobile Money",
            mobile_number="1234567890",
        )

        self.list_create_url = reverse("api:transactions:payment_methods_list_create")
        self.detail_url = reverse(
            "api:transactions:payment_method_detail",
            kwargs={"pk": self.card_payment.pk},
        )

    def test_list_payment_methods(self):
        response = self.client.get(self.list_create_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        card_data = next(item for item in response.data if item["type"] == "card")
        self.assertEqual(
            card_data["masked_card_number"], self.card_payment.masked_card_number
        )
        self.assertTrue(card_data["default_method"])
        # Check for transaction fees and payment method type name
        self.assertIn("cash_in_transaction_fee", card_data)
        self.assertIn("cash_out_transaction_fee", card_data)
        self.assertIn("payment_method_type_name", card_data)

        mobile_data = next(
            item for item in response.data if item["type"] == "mobile_money"
        )
        self.assertEqual(mobile_data["provider"], self.mobile_payment.provider)
        self.assertEqual(
            mobile_data["mobile_number"], self.mobile_payment.mobile_number
        )
        self.assertFalse(mobile_data["default_method"])
        # Check for transaction fees and payment method type name
        self.assertIn("cash_in_transaction_fee", mobile_data)
        self.assertIn("cash_out_transaction_fee", mobile_data)
        self.assertIn("payment_method_type_name", mobile_data)

    def test_create_card_payment_method_with_type(self):
        data = {
            "type": "card",
            "cardholder_name": "Jane Doe",
            "card_number": "4111 1111 1111 1111",
            "expiry_date": "12/2025",
            "cvv": "123",
            "billing_address": "456 Main St, City, Country",
            "payment_method_type": self.visa_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cardholder_name"], "Jane Doe")
        self.assertEqual(response.data["masked_card_number"], "**** **** **** 1111")
        self.assertEqual(response.data["expiry_date"], "12/2025")
        self.assertNotIn("card_number", response.data)
        self.assertNotIn("cvv", response.data)

        payment_method = PaymentMethod.objects.get(pk=response.data["id"])
        self.assertEqual(payment_method.cardholder_name, "Jane Doe")
        self.assertEqual(payment_method.masked_card_number, "**** **** **** 1111")
        self.assertEqual(payment_method.type, "card")
        self.assertFalse(payment_method.default_method)

    def test_create_mobile_money_payment_method_with_type(self):
        from phonenumber_field.phonenumber import PhoneNumber

        # Create a valid phone number for Cameroon
        phone_number = "+237670000000"

        data = {
            "type": "mobile_money",
            "provider": "MTN Mobile Money",
            "mobile_number": phone_number,
            "payment_method_type": self.mtn_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")

        print("Response data:", response.data)  # Print response data for debugging

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["provider"], "MTN Mobile Money")
        self.assertEqual(response.data["mobile_number"], phone_number)

        payment_method = PaymentMethod.objects.get(pk=response.data["id"])
        self.assertEqual(payment_method.provider, "MTN Mobile Money")
        self.assertEqual(payment_method.mobile_number, phone_number)
        self.assertEqual(payment_method.type, "mobile_money")
        self.assertFalse(payment_method.default_method)

    def test_retrieve_payment_method(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.card_payment.pk)
        self.assertEqual(response.data["type"], "card")
        self.assertEqual(
            response.data["masked_card_number"], self.card_payment.masked_card_number
        )

    def test_update_payment_method(self):
        data = {"cardholder_name": "Updated Name", "billing_address": "Updated Address"}

        response = self.client.patch(self.detail_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cardholder_name"], "Updated Name")
        self.assertEqual(response.data["billing_address"], "Updated Address")

        self.card_payment.refresh_from_db()
        self.assertEqual(self.card_payment.cardholder_name, "Updated Name")
        self.assertEqual(self.card_payment.billing_address, "Updated Address")

    def test_delete_payment_method(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(PaymentMethod.DoesNotExist):
            PaymentMethod.objects.get(pk=self.card_payment.pk)

    def test_authentication_required(self):
        client = APIClient()

        response = client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.post(self.list_create_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.patch(self.detail_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_only_access_own_payment_methods(self):
        other_user = UserFactory.create()
        other_payment = PaymentMethod.objects.create(
            user=other_user,
            type="card",
            cardholder_name="Other User",
            masked_card_number="**** **** **** 5678",
        )

        other_detail_url = reverse(
            "api:transactions:payment_method_detail", kwargs={"pk": other_payment.pk}
        )
        response = self.client.get(other_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_prevent_duplicate_card_payment_method(self):
        """Test that creating a duplicate card payment method returns an error"""
        # First create a card payment method
        data = {
            "type": "card",
            "cardholder_name": "Jane Doe",
            "card_number": "4111 1111 1111 1111",
            "expiry_date": "12/2025",
            "cvv": "123",
            "billing_address": "456 Main St, City, Country",
            "payment_method_type": self.visa_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Try to create another card payment method with the same card number
        data = {
            "type": "card",
            "cardholder_name": "Different Name",
            "card_number": "4111 1111 1111 1111",  # Same card number
            "expiry_date": "12/2026",  # Different expiry date
            "cvv": "456",  # Different CVV
            "billing_address": "789 Other St, City, Country",  # Different address
            "payment_method_type": self.visa_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("card_number", response.data)
        self.assertIn("already exists", response.data["card_number"][0])

    def test_prevent_duplicate_mobile_money_payment_method(self):
        """Test that creating a duplicate mobile money payment method returns an error"""
        # First create a mobile money payment method
        from phonenumber_field.phonenumber import PhoneNumber

        # Create a valid phone number for Cameroon
        phone_number = "+237670000000"

        data = {
            "type": "mobile_money",
            "provider": "MTN Mobile Money",
            "mobile_number": phone_number,
            "payment_method_type": self.mtn_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Try to create another mobile money payment method with the same provider and mobile number
        data = {
            "type": "mobile_money",
            "provider": "MTN Mobile Money",  # Same provider
            "mobile_number": phone_number,  # Same mobile number
            "payment_method_type": self.mtn_type.id,
        }

        response = self.client.post(self.list_create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mobile_number", response.data)
        self.assertIn("already exists", response.data["mobile_number"][0])


class AddFundsTransactionAPITestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a BUSINESS wallet for the user
        self.wallet = Wallet.objects.create(
            user=self.user, wallet_type=WalletType.BUSINESS, balance=0
        )

        # Create a payment method type with a specific cash-in transaction fee
        self.payment_method_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="MTN Mobile Money",
                cash_in_transaction_fee=2.5,  # 2.5% fee
            )
        )

        # Create a payment method for the user with the payment method type
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN Mobile Money",
            mobile_number="+237670000000",
            payment_method_type=self.payment_method_type,
        )

        self.add_funds_url = reverse("api:transactions:transactions_cash_in")
        self.callback_url = reverse("api:transactions:transactions_cash_in_callback")

    def test_initiate_add_funds_transaction(self):
        amount = 1000
        data = {
            "amount": amount,
            "payment_method_id": self.payment_method.id,
            "wallet_id": self.wallet.id,
        }

        response = self.client.post(self.add_funds_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the response includes the charged amount and calculated fee
        expected_fee = (amount * self.payment_method_type.cash_in_transaction_fee) / 100
        expected_charged_amount = amount + expected_fee

        self.assertIn("calculated_fee", response.data)
        self.assertIn("charged_amount", response.data)
        self.assertEqual(response.data["calculated_fee"], expected_fee)
        self.assertEqual(response.data["charged_amount"], expected_charged_amount)

        # Verify a transaction was created
        transaction = Transaction.objects.filter(
            type=TransactionType.CashIn,
            payment_method=self.payment_method,
            wallet=self.wallet,
            amount=amount,
        ).first()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.status, TransactionStatus.INITIATED)

        # Verify the charged amount and calculated fee
        self.assertEqual(transaction.calculated_fee, expected_fee)
        self.assertEqual(transaction.charged_amount, expected_charged_amount)

    def test_add_funds_callback_success(self):
        # First create a transaction
        amount = 1000
        transaction = Transaction.objects.create(
            type=TransactionType.CashIn,
            status=TransactionStatus.INITIATED,
            amount=amount,
            calculated_fee=25.0,  # 2.5% of 1000
            charged_amount=1025.0,  # 1000 + 25
            payment_method=self.payment_method,
            wallet=self.wallet,
            reference=make_transaction_ref(TransactionType.CashIn),
            payment_code=make_payment_code(
                make_transaction_ref(TransactionType.CashIn),
                TransactionType.CashIn,
            ),
        )

        # Initial wallet balance
        initial_balance = self.wallet.balance

        # Call the callback with success
        data = {
            "transaction_reference": transaction.reference,
            "status": "success",
            "processor_reference": "ext-ref-123",
        }

        response = self.client.post(self.callback_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh the transaction and wallet
        transaction.refresh_from_db()
        self.wallet.refresh_from_db()

        # Verify the transaction was completed
        self.assertEqual(transaction.status, TransactionStatus.COMPLETED)

        # Verify the wallet balance was updated with the original amount (not the charged amount)
        # The charged amount includes the fee which is kept by the payment processor
        self.assertEqual(self.wallet.balance, initial_balance + amount)

    def test_add_funds_callback_failure(self):
        # First create a transaction
        transaction = Transaction.objects.create(
            type=TransactionType.CashIn,
            status=TransactionStatus.INITIATED,
            amount=1000,
            payment_method=self.payment_method,
            wallet=self.wallet,
            reference=make_transaction_ref(TransactionType.CashIn),
            payment_code=make_payment_code(
                make_transaction_ref(TransactionType.CashIn),
                TransactionType.CashIn,
            ),
        )

        # Initial wallet balance
        initial_balance = self.wallet.balance

        # Call the callback with failure
        data = {
            "transaction_reference": transaction.reference,
            "status": "failed",
            "failure_reason": "Payment declined by provider",
        }

        response = self.client.post(self.callback_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh the transaction and wallet
        transaction.refresh_from_db()
        self.wallet.refresh_from_db()

        # Verify the transaction was marked as failed
        self.assertEqual(transaction.status, TransactionStatus.FAILED)

        # Verify the wallet balance was not updated
        self.assertEqual(self.wallet.balance, initial_balance)

    def test_add_funds_callback_transaction_not_found(self):
        # Call the callback with a non-existent transaction reference
        data = {
            "transaction_reference": "non-existent-reference",
            "status": "success",
        }

        response = self.client.post(self.callback_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentMethodTypeAPITestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.country = AvailableCountryFactory.create(
            name="Cameroon", iso_code="CM", dial_code="237"
        )
        self.other_country = AvailableCountryFactory.create(
            name="Nigeria", iso_code="NG", dial_code="234"  # Different dial code
        )

        # Create card payment method types
        self.visa = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Visa", country=self.country
        )
        self.mastercard = PaymentMethodTypeFactory.create_card_payment_method_type(
            name="Mastercard", country=self.country
        )

        # Create mobile money payment method types
        self.mtn = PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
            name="MTN Mobile Money", country=self.country
        )
        self.orange = PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
            name="Orange Money", country=self.country
        )

        # Create payment method type for another country
        self.other_country_type = (
            PaymentMethodTypeFactory.create_mobile_money_payment_method_type(
                name="Other Country Provider", country=self.other_country
            )
        )

        self.list_url = reverse("api:transactions:payment-method-types-list")

    def test_list_payment_method_types(self):
        """Test that authenticated users can list all payment method types"""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)  # All payment method types

        # Check that the response includes the expected fields
        visa_data = next(item for item in response.data if item["name"] == "Visa")
        self.assertEqual(visa_data["code"], "CARD_VISA")
        self.assertEqual(visa_data["country_name"], "Cameroon")
        self.assertEqual(visa_data["country_code"], "CM")
        self.assertIn("required_fields", visa_data)

        # Check required fields for card payment method type
        self.assertIn("cardholder_name", visa_data["required_fields"])
        self.assertIn("card_number", visa_data["required_fields"])
        self.assertIn("expiry_date", visa_data["required_fields"])
        self.assertIn("cvv", visa_data["required_fields"])
        self.assertIn("billing_address", visa_data["required_fields"])

        # Check required fields for mobile money payment method type
        mtn_data = next(
            item for item in response.data if item["name"] == "MTN Mobile Money"
        )
        self.assertIn("provider", mtn_data["required_fields"])
        self.assertIn("mobile_number", mtn_data["required_fields"])

    def test_filter_payment_method_types_by_country_id(self):
        """Test that payment method types can be filtered by country ID"""
        response = self.client.get(f"{self.list_url}?country_id={self.country.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 4
        )  # Only payment method types for the specified country

        # Check that all returned payment method types are for the specified country
        for item in response.data:
            self.assertEqual(item["country_name"], "Cameroon")

    def test_filter_payment_method_types_by_country_code(self):
        """Test that payment method types can be filtered by country code"""
        response = self.client.get(
            f"{self.list_url}?country_code={self.country.iso_code}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 4
        )  # Only payment method types for the specified country

        # Check that all returned payment method types are for the specified country
        for item in response.data:
            self.assertEqual(item["country_code"], "CM")

    def test_authentication_required(self):
        """Test that authentication is required to list payment method types"""
        client = APIClient()  # Unauthenticated client

        response = client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
