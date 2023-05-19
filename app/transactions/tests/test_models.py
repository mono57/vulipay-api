from django.test import TestCase

from app.accounts.models import Account
from app.accounts.tests import factories as f
from app.transactions.models import Transaction, TransactionStatus, TransactionType

class TransactionTestCase(TestCase):
    def setUp(self):
        country = f.AvailableCountryFactory.create()
        self.payer_account = f.AccountFactory.create(country=country)
        self.receiver_account = f.AccountFactory.create(country=country, intl_phone_number="237698049743")


    def test_it_should_return_reference_on_str(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000,
            receiver_account=self.receiver_account)

        self.assertEqual(transaction.reference, str(transaction))

    def test_it_should_create_P2P_transaction(self):
        transaction = Transaction.create_P2P_transaction(
            amount=2000,
            receiver_account=self.receiver_account)

        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(float(2000), transaction.amount)
        self.assertEqual(TransactionType.P2P, transaction.type)
        self.assertEqual(TransactionStatus.INITIATED, transaction.status)
        self.assertIsNotNone(transaction.payment_code)
        self.assertIsNotNone(transaction.reference)
        self.assertIsNotNone(transaction.receiver_account)
        self.assertIsNone(transaction.payer_account)