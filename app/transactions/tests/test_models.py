from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TransactionTestCase

from app.accounts.models import AvailableCountry, Currency
from app.accounts.tests import factories as f
from app.accounts.tests.factories import UserFactory
from app.transactions.models import (
    PaymentMethod,
    PaymentMethodType,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)
from app.transactions.tests.factories import (
    AvailableCountryFactory,
    TransactionFactory,
    WalletFactory,
)


class PaymentMethodModelTestCase(TransactionTestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def test_create_card_payment_method(self):
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            type="card",
            cardholder_name="John Doe",
            masked_card_number="**** **** **** 1234",
            expiry_date="12/2025",
            cvv_hash="hashed_cvv",
            billing_address="123 Main St, City, Country",
        )

        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.type, "card")
        self.assertEqual(payment_method.cardholder_name, "John Doe")
        self.assertEqual(payment_method.masked_card_number, "**** **** **** 1234")
        self.assertEqual(payment_method.expiry_date, "12/2025")
        self.assertEqual(payment_method.cvv_hash, "hashed_cvv")
        self.assertEqual(payment_method.billing_address, "123 Main St, City, Country")
        self.assertTrue(payment_method.default_method)

    def test_create_mobile_money_payment_method(self):
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN Mobile Money",
            mobile_number="1234567890",
        )

        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.type, "mobile_money")
        self.assertEqual(payment_method.provider, "MTN Mobile Money")
        self.assertEqual(payment_method.mobile_number, "1234567890")
        self.assertTrue(payment_method.default_method)

    def test_default_payment_method_behavior(self):
        payment_method1 = PaymentMethod.objects.create(
            user=self.user,
            type="card",
            cardholder_name="John Doe",
            masked_card_number="**** **** **** 1234",
        )

        payment_method2 = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN Mobile Money",
            mobile_number="1234567890",
        )

        payment_method1.refresh_from_db()
        payment_method2.refresh_from_db()
        self.assertTrue(payment_method1.default_method)
        self.assertFalse(payment_method2.default_method)

        payment_method2.default_method = True
        payment_method2.save()

        payment_method1.refresh_from_db()
        payment_method2.refresh_from_db()
        self.assertFalse(payment_method1.default_method)
        self.assertTrue(payment_method2.default_method)

    def test_string_representation(self):
        card = PaymentMethod.objects.create(
            user=self.user, type="card", masked_card_number="**** **** **** 1234"
        )

        mobile = PaymentMethod.objects.create(
            user=self.user,
            type="mobile_money",
            provider="MTN",
            mobile_number="1234567890",
        )

        self.assertEqual(str(card), "Card: **** **** **** 1234")
        self.assertEqual(str(mobile), "Mobile Money: MTN - 1234567890")


class WalletModelTestCase(TransactionTestCase):
    def setUp(self):
        self.user = UserFactory.create()

        self.main_wallet = Wallet.objects.get(
            user=self.user, wallet_type=WalletType.MAIN
        )

        self.main_wallet.balance = 1000
        self.main_wallet.save()

        self.other_user = UserFactory.create()
        self.other_main_wallet = Wallet.objects.get(
            user=self.other_user, wallet_type=WalletType.MAIN
        )
        self.other_main_wallet.balance = 2000
        self.other_main_wallet.save()

        self.other_business_wallet = WalletFactory.create_business_wallet(
            user=self.other_user, balance=3000
        )

    def test_wallet_creation(self):
        self.assertEqual(self.main_wallet.user, self.user)
        self.assertEqual(self.main_wallet.wallet_type, WalletType.MAIN)
        self.assertEqual(self.main_wallet.balance, 1000)
        self.assertTrue(self.main_wallet.is_active)

        business_wallet = WalletFactory.create_business_wallet(
            user=self.user, balance=2000
        )
        self.assertEqual(business_wallet.user, self.user)
        self.assertEqual(business_wallet.wallet_type, WalletType.BUSINESS)
        self.assertEqual(business_wallet.balance, 2000)
        self.assertTrue(business_wallet.is_active)

        with self.assertRaises(IntegrityError):
            Wallet.objects.create(user=self.user, wallet_type=WalletType.MAIN)

    def test_wallet_deposit(self):
        new_balance = self.main_wallet.deposit(500)
        self.assertEqual(new_balance, 1500)
        self.main_wallet.refresh_from_db()
        self.assertEqual(self.main_wallet.balance, 1500)

        with self.assertRaises(ValueError):
            self.main_wallet.deposit(-100)

    def test_wallet_withdraw(self):
        new_balance = self.main_wallet.withdraw(500)
        self.assertEqual(new_balance, 500)
        self.main_wallet.refresh_from_db()
        self.assertEqual(self.main_wallet.balance, 500)

        with self.assertRaises(ValueError):
            self.main_wallet.withdraw(-100)

        with self.assertRaises(ValueError):
            self.main_wallet.withdraw(1000)

    def test_wallet_transfer(self):
        business_wallet = WalletFactory.create_business_wallet(
            user=self.user, balance=0
        )
        result = self.main_wallet.transfer(business_wallet, 500)

        self.assertTrue(result)
        self.main_wallet.refresh_from_db()
        business_wallet.refresh_from_db()
        self.assertEqual(self.main_wallet.balance, 500)
        self.assertEqual(business_wallet.balance, 500)

        result = self.main_wallet.transfer(self.other_main_wallet, 200)

        self.assertTrue(result)
        self.main_wallet.refresh_from_db()
        self.other_main_wallet.refresh_from_db()
        self.assertEqual(self.main_wallet.balance, 300)
        self.assertEqual(self.other_main_wallet.balance, 2200)

        with self.assertRaises(ValueError):
            self.main_wallet.transfer(business_wallet, -100)

        with self.assertRaises(ValueError):
            self.main_wallet.transfer(business_wallet, 1000)

    def test_string_representation(self):
        self.assertEqual(str(self.main_wallet), f"{self.user.email}'s Main Wallet")

        business_wallet = WalletFactory.create_business_wallet(user=self.user)
        self.assertEqual(str(business_wallet), f"{self.user.email}'s Business Wallet")


class PaymentMethodTypeTestCase(TransactionTestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()
        self.payment_method_type = PaymentMethodType.objects.create(
            name="Credit Card",
            code="CREDIT_CARD",
            cash_in_transaction_fee=1.5,
            cash_out_transaction_fee=2.0,
            country=self.country,
        )

    def test_payment_method_type_creation(self):
        self.assertEqual(self.payment_method_type.name, "Credit Card")
        self.assertEqual(self.payment_method_type.code, "CREDIT_CARD")
        self.assertEqual(self.payment_method_type.cash_in_transaction_fee, 1.5)
        self.assertEqual(self.payment_method_type.cash_out_transaction_fee, 2.0)
        self.assertEqual(self.payment_method_type.country, self.country)

    def test_string_representation(self):
        self.assertEqual(str(self.payment_method_type), "Credit Card")

    def test_payment_method_type_with_null_country(self):
        payment_method_type = PaymentMethodType.objects.create(
            name="Mobile Money",
            code="MOBILE_MONEY",
            cash_in_transaction_fee=1.0,
            cash_out_transaction_fee=1.5,
            country=None,
        )
        self.assertIsNone(payment_method_type.country)

    def test_payment_method_type_with_null_fees(self):
        payment_method_type = PaymentMethodType.objects.create(
            name="Bank Transfer",
            code="BANK_TRANSFER",
            cash_in_transaction_fee=None,
            cash_out_transaction_fee=None,
            country=self.country,
        )
        self.assertIsNone(payment_method_type.cash_in_transaction_fee)
        self.assertIsNone(payment_method_type.cash_out_transaction_fee)

    def test_payment_method_type_update(self):
        self.payment_method_type.name = "Updated Credit Card"
        self.payment_method_type.cash_in_transaction_fee = 2.5
        self.payment_method_type.save()

        self.payment_method_type.refresh_from_db()

        self.assertEqual(self.payment_method_type.name, "Updated Credit Card")
        self.assertEqual(self.payment_method_type.cash_in_transaction_fee, 2.5)


class WalletCurrencyTestCase(TransactionTestCase):
    def test_wallet_currency_auto_set_from_user_country_with_currency(self):
        # Create a country with a currency set
        country = AvailableCountry.objects.create(
            name="Test Country with Currency",
            dial_code="456",
            iso_code="TCC",
            phone_number_regex=r"^\+456\d{8}$",
            currency="TCC-CURRENCY",
        )

        # Create a user with the country
        user = UserFactory.create(country=country)

        # Remove any existing wallets for this user to avoid conflicts
        Wallet.objects.filter(user=user).delete()

        # Create a wallet for the user
        wallet = Wallet.objects.create(
            user=user,
            wallet_type=WalletType.MAIN,
            balance=0,
        )

        # Check that the currency was set from the country's currency field
        self.assertEqual(wallet.currency, "TCC-CURRENCY")

    def test_wallet_currency_auto_set_from_mapping(self):
        # Create a country without setting the currency field
        country = AvailableCountry.objects.create(
            name="Test Country",
            dial_code="123",
            iso_code="TC",
            phone_number_regex=r"^\+123\d{8}$",
        )

        # Create a user with the country
        user = UserFactory.create(country=country)

        # Remove any existing wallets for this user to avoid conflicts
        Wallet.objects.filter(user=user).delete()

        # Create a wallet for the user
        wallet = Wallet.objects.create(
            user=user,
            wallet_type=WalletType.MAIN,
            balance=0,
        )

        # Check that the currency was automatically set using the mapping
        self.assertEqual(wallet.currency, "TC Currency")

    def test_wallet_currency_not_set_without_user_country(self):
        # Create a user without a country
        user = UserFactory.create(country=None)

        # Remove any existing wallets for this user to avoid conflicts
        Wallet.objects.filter(user=user).delete()

        # Create a wallet for the user
        wallet = Wallet.objects.create(
            user=user,
            wallet_type=WalletType.MAIN,
            balance=0,
        )

        # Check that the currency was not set
        self.assertIsNone(wallet.currency)

    def test_wallet_currency_not_overridden_if_provided(self):
        # Create a country
        country = AvailableCountry.objects.create(
            name="Country 1",
            dial_code="111",
            iso_code="CM",  # Cameroon
            phone_number_regex=r"^\+111\d{8}$",
            currency="XAF",  # Set currency for the country
        )

        # Create a user with country
        user = UserFactory.create(country=country)

        # Remove any existing wallets for this user to avoid conflicts
        Wallet.objects.filter(user=user).delete()

        # Create a wallet for the user with explicit currency
        custom_currency = "USD"
        wallet = Wallet.objects.create(
            user=user,
            wallet_type=WalletType.MAIN,
            balance=0,
            currency=custom_currency,
        )

        # Check that the currency was not overridden by the user's country currency
        self.assertEqual(wallet.currency, custom_currency)
        # The auto-assigned currency would be XAF for Cameroon
        self.assertNotEqual(wallet.currency, "XAF")
