import json

from django.urls import reverse
from phonenumber_field.phonenumber import PhoneNumber
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import Account
from app.accounts.tests import factories as f
from app.accounts.tests.factories import (
    AccountFactory,
    AvailableCountryFactory,
    CarrierFactory,
    PhoneNumberFactory,
    UserFactory,
)
from app.core.utils import APIViewTestCase, make_payment_code, make_transaction_ref
from app.transactions.api.views import P2PTransactionCreateAPIView
from app.transactions.models import (
    PaymentMethod,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)
from app.transactions.tests.factories import (
    PaymentMethodTypeFactory,
    TransactionFactory,
    TransactionFeeFactory,
)


class P2PTransactionCreateAPIViewTestCase(APIViewTestCase):
    view_name = "api:transactions:transactions_p2p_transactions"

    def setUp(self):
        super().setUp()

        self.account: Account = f.AccountFactory.create()
        self.access_token = str(RefreshToken.for_user(self.account).access_token)

    def test_it_should_not_create_transation_for_unauthorized_user(self):
        response = self.view_post({})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_create_P2P_transaction(self):
        self.authenticate_with_jwttoken(self.access_token)

        payload = {"amount": 2000}

        response = self.view_post(payload)
        data = response.data

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_code", data)
        self.assertIsNotNone(data.get("payment_code"))

        transaction = Transaction.objects.filter(
            payment_code=data.get("payment_code")
        ).first()

        self.assertEqual(transaction.amount, float(payload.get("amount")))

    def test_it_should_not_create_transaction_for_wrong_amount(self):
        self.authenticate_with_jwttoken(self.access_token)

        payload = {"amount": -2000}
        response = self.view_post(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payload["amount"] = 0
        response = self.view_post(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TransactionDetailsRetrieveAPIView(APIViewTestCase):
    view_name = "api:transactions:transactions_transaction_details"

    def setUp(self):
        super().setUp()
        self.account = f.AccountFactory.create()
        self.transaction = Transaction.create_P2P_transaction(2000, self.account)
        self.payment_code = self.transaction.payment_code
        self.access_token = str(RefreshToken.for_user(self.account).access_token)

    def test_it_should_not_get_details_for_unauthorized_account(self):
        response = self.view_get(reverse_kwargs={"payment_code": self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_raise_invalid_vulipay_payment_code(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_get(
            reverse_kwargs={
                "payment_code": "vulipay$SE2$SDFG34GE3G4234G42345G4F3ERF34G543FD3F4G54F"
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_it_should_get_transaction_details(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_get(reverse_kwargs={"payment_code": self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MPTransactionCreateAPIViewTestCase(APIViewTestCase):
    view_name = "api:transactions:transactions_mp_transactions"

    def setUp(self):
        super().setUp()

        self.receiver_account = f.AccountFactory.create()
        self.payer_account = f.AccountFactory.create(
            country=self.receiver_account.country
        )
        self.fake_amount = 2000

        self.payload = {
            "amount": self.fake_amount,
            "receiver_account": self.receiver_account.number,
        }
        self.access_token = str(RefreshToken.for_user(self.payer_account).access_token)

    def test_it_should_raise_unauthorized_error(self):
        response = self.view_post(self.payload)

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_it_should_not_create_transaction_for_empty_receiver_account(self):
        self.authenticate_with_jwttoken(self.access_token)

        payload = {**self.payload, "receiver_account": ""}

        response = self.view_post(payload)
        data = response.data

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("receiver_account", data)

    def test_it_should_create_mp_transaction(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_post(self.payload)

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("receiver_account", data)


class ValidateTransactionUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:transactions:transactions_transaction_validate"

    def setUp(self):
        super().setUp()
        self.payer_account: Account = f.AccountFactory.create(balance=2000)
        self.payer_account.set_pin("2314")
        self.country = self.payer_account.country
        self.receiver_account = f.AccountFactory.create(country=self.country)

    def test_it_should_raise_permissions_denied_on_wrong_password(self):
        self.authenticate_with_account(self.payer_account)
        transaction: Transaction = TransactionFactory.create_p2p_transaction(
            receiver_account=self.receiver_account,
            payer_account=self.payer_account,
        )
        payload = {"pin": "2324"}

        response = self.view_put(
            data=payload, reverse_kwargs={"reference": transaction.reference}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_it_should_raise_permission_denied_on_insufficient_balance(self):
        self.authenticate_with_account(self.payer_account)
        TransactionFeeFactory.create_p2p_transaction_fee(country=self.country)
        transaction: Transaction = TransactionFactory.create_p2p_transaction(
            receiver_account=self.receiver_account,
            payer_account=self.payer_account,
            amount=5000,
        )
        payload = {"pin": "2314"}

        response = self.view_put(
            data=payload, reverse_kwargs={"reference": transaction.reference}
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_it_should_validate_transaction(self):
        self.authenticate_with_account(self.payer_account)
        TransactionFeeFactory.create_p2p_transaction_fee(country=self.country)
        transaction: Transaction = TransactionFactory.create_p2p_transaction(
            receiver_account=self.receiver_account,
            payer_account=self.payer_account,
            amount=1000,
            status=TransactionStatus.PENDING,
        )
        payload = {"pin": "2314"}

        response = self.view_put(
            data=payload, reverse_kwargs={"reference": transaction.reference}
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)


class TransactionPairingUpdateAPIViewTestCase(APIViewTestCase):
    view_name = "api:transactions:transactions_transaction_pairing"

    def setUp(self):
        super().setUp()
        self.receiver_account = AccountFactory.create()
        self.country = self.receiver_account.country
        TransactionFeeFactory.create_p2p_transaction_fee(country=self.country)
        self.transaction: Transaction = TransactionFactory.create_p2p_transaction(
            receiver_account=self.receiver_account, amount=5000
        )
        self.payment_code = self.transaction.payment_code

    def test_it_should_pair_account(self):
        payer_account = AccountFactory.create(country=self.country, balance=10000)

        self.authenticate_with_account(payer_account)
        response = self.view_put(reverse_kwargs={"payment_code": self.payment_code})

        data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(data.get("payer_account"))
        self.assertIsNotNone(data.get("charged_amount"))
        self.assertIsNotNone(data.get("calculated_fee"))

    def test_it_should_raise_insufficient_balance(self):
        payer_account = AccountFactory.create(country=self.country, balance=5000)

        self.authenticate_with_account(payer_account)
        response = self.view_put(reverse_kwargs={"payment_code": self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CashOutTransactionCreateAPIViewTest(APIViewTestCase):
    view_name = "api:transactions:transactions_co_transactions"

    def setUp(self):
        super().setUp()
        self.account: Account = AccountFactory.create(balance=10000)
        self.account.set_pin("2314")
        self.country = self.account.country
        carrier = CarrierFactory.create(country=self.country)
        PhoneNumberFactory.create(account=self.account, carrier=carrier)
        TransactionFeeFactory.create_co_transaction_fee(country=self.country)

    def test_it_should_create_transaction(self):
        self.authenticate_with_account(self.account)
        payload = {"intl_phone_number": "237698049741", "amount": 5000, "pin": "2314"}

        response = self.view_post(data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


class CashInTransactionCreateAPIViewTest(APIViewTestCase):
    view_name = "api:transactions:transactions_ci_transactions"

    def setUp(self):
        super().setUp()
        self.account: Account = AccountFactory.create(balance=10000)
        self.country = self.account.country
        carrier = CarrierFactory.create(country=self.country)
        PhoneNumberFactory.create(account=self.account, carrier=carrier)
        TransactionFeeFactory.create_ci_transaction_fee(country=self.country)

    def test_it_should_create_transaction(self):
        self.authenticate_with_account(self.account)
        payload = {"intl_phone_number": "237698049741", "amount": 5000}

        response = self.view_post(data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


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

        # Create a payment method for the user
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN Mobile Money",
            mobile_number="+237670000000",
        )

        self.add_funds_url = reverse("api:transactions:transactions_cash_in")
        self.callback_url = reverse("api:transactions:transactions_cash_in_callback")

    def test_initiate_add_funds_transaction(self):
        data = {
            "amount": 1000,
            "payment_method_id": self.payment_method.id,
            "wallet_id": self.wallet.id,
        }

        response = self.client.post(self.add_funds_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify a transaction was created
        transaction = Transaction.objects.filter(
            type=TransactionType.CashIn,
            payment_method=self.payment_method,
            wallet=self.wallet,
            amount=1000,
        ).first()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.status, TransactionStatus.INITIATED)

    def test_add_funds_callback_success(self):
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

        # Verify the wallet balance was updated
        self.assertEqual(self.wallet.balance, initial_balance + 1000)

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
