from unittest.mock import MagicMock, patch

from django.test import TransactionTestCase

from app.accounts.tests import factories as f
from app.accounts.tests.factories import UserFactory
from app.transactions.models import (
    PaymentMethod,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)
from app.transactions.tests.factories import TransactionFactory, WalletFactory


class TransactionTestCase(TransactionTestCase):
    def setUp(self):
        self.payer_account = f.AccountFactory.create()
        self.receiver_account = f.AccountFactory.create(
            country=self.payer_account.country, intl_phone_number="237698049743"
        )
        self.transaction: Transaction = TransactionFactory.create_p2p_transaction(
            receiver_account=self.receiver_account
        )

    def test_it_should_return_reference_on_str(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000, receiver_account=self.receiver_account
        )

        self.assertEqual(transaction.reference, str(transaction))

    def test_it_should_create_P2P_transaction(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000, receiver_account=self.receiver_account
        )

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(float(2000), transaction.amount)
        self.assertEqual(TransactionType.P2P, transaction.type)
        self.assertEqual(TransactionStatus.INITIATED, transaction.status)
        self.assertIsNotNone(transaction.payment_code)
        self.assertIsNotNone(transaction.reference)
        self.assertIsNotNone(transaction.receiver_account)
        self.assertIsNone(transaction.payer_account)

    @patch("app.transactions.managers.TransactionManager._create")
    def test_it_should_create_MP_transaction(
        self, mocked_create_transaction: MagicMock
    ):
        amount = 2000

        Transaction.create_MP_transaction(
            amount=amount,
            receiver_account=self.receiver_account,
            payer_account=self.payer_account,
        )
        call_kwargs = mocked_create_transaction.call_args.kwargs

        mocked_create_transaction.assert_called_once()

        self.assertEqual(call_kwargs["amount"], amount)
        self.assertEqual(call_kwargs["receiver_account"], self.receiver_account)
        self.assertEqual(call_kwargs["payer_account"], self.payer_account)

    @patch("app.transactions.models.Transaction.save")
    @patch("app.transactions.models.Transaction.set_as_PENDING")
    def test_it_should_pair_account(
        self, mocked_set_as_pending: MagicMock, mocked_save: MagicMock
    ):
        self.transaction.pair(self.payer_account)
        mocked_set_as_pending.assert_called_once()
        mocked_save.assert_called_once()

    def test_it_should_get_inclusive_amount(self):
        pass

    @patch("app.accounts.models.Account.debit")
    @patch("app.accounts.models.Account.credit")
    @patch("app.accounts.models.Account.credit_master_account")
    def test_it_should_perform_payment(
        self,
        mocked_credit_master: MagicMock,
        mocked_credit_receiver: MagicMock,
        mocked_debit_payer: MagicMock,
    ):
        transaction: Transaction = TransactionFactory.create_pending_transaction(
            receiver_account=self.receiver_account, payer_account=self.payer_account
        )

        transaction.perform_payment()

        mocked_credit_master.assert_called_once_with(transaction.calculated_fee)
        mocked_credit_receiver.assert_called_once_with(transaction.amount)
        mocked_debit_payer.assert_called_once_with(transaction.charged_amount)


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
