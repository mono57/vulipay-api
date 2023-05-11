from django.test import TestCase

from app.accounts.models import Account
from app.transactions.models import Transaction, TransactionStatus, TransactionType

class TransactionTestCase(TestCase):
    def setUp(self):
        self.payer_account = Account.objects.create()
        self.receiver_account = Account.objects.create()


    def test_it_should_return_reference_on_str(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000,
            payer_account=self.payer_account)

        self.assertEqual(transaction.reference, str(transaction))

    def test_it_should_create_P2P_transaction(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000,
            payer_account=self.payer_account)

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(float(2000), transaction.amount)
        self.assertEqual(TransactionType.P2P, transaction.type)
        self.assertEqual(TransactionStatus.INITIATED, transaction.status)
        self.assertIsNotNone(transaction.payment_code)
        self.assertIsNotNone(transaction.reference)