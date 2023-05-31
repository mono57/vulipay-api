from unittest.mock import patch, MagicMock
from django.test import TestCase

from app.accounts.models import Account
from app.accounts.tests import factories as f
from app.transactions.models import Transaction, TransactionStatus, TransactionType


class TransactionTestCase(TestCase):
    def setUp(self):
        self.payer_account = f.AccountFactory.create()
        self.receiver_account = f.AccountFactory.create(
            country=self.payer_account.country, intl_phone_number="237698049743"
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
