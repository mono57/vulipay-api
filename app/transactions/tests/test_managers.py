from unittest.mock import MagicMock, patch

from django.test import TestCase

from app.accounts.tests.factories import AccountFactory, AvailableCountryFactory
from app.transactions.models import (
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
)
from app.transactions.tests.factories import TransactionFeeFactory


class TransactionManagerTestCase(TestCase):
    def setUp(self) -> None:
        self.receiver_account = AccountFactory.create()
        self.payer_account = AccountFactory.create(
            phone_number="698030421", country=self.receiver_account.country
        )
        self.fake_transaction_ref = "P2P.DF2422.1683740925"
        self.fake_payment_code = (
            "vulipay$P2P$SDFG34GE3G4234G42345G4F3ERF34G543FD3F4G54F"
        )

    @patch("app.transactions.managers.make_transaction_ref")
    @patch("app.transactions.managers.make_payment_code")
    def test_it_should_create_transaction(
        self,
        mocked_make_payment_code: MagicMock,
        mocked_make_transaction_ref: MagicMock,
    ):
        mocked_make_transaction_ref.return_value = self.fake_transaction_ref
        mocked_make_payment_code.return_value = self.fake_payment_code

        t: Transaction = Transaction.objects._create(
            type=TransactionType.MP,
            amount=2000,
            receiver_account=self.receiver_account,
            payer_account=self.payer_account,
            status=TransactionStatus.PENDING,
            notes="notes",
        )

        self.assertEqual(t.reference, self.fake_transaction_ref)
        self.assertEqual(t.payment_code, self.fake_payment_code)
        self.assertEqual(t.type, TransactionType.MP)
        self.assertEqual(t.amount, float(2000))
        self.assertEqual(t.payer_account, self.payer_account)
        self.assertEqual(t.receiver_account, self.receiver_account)
        self.assertEqual(t.status, TransactionStatus.PENDING)


class TransactionFeeManagerTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.country = AvailableCountryFactory.create()
        self.transaction_fee = TransactionFeeFactory.create_p2p_transaction_fee(
            country=self.country
        )

    def test_it_get_applicable_fee(self):
        applicable_fee = TransactionFee.objects.get_applicable_fee(
            country=self.country, transaction_type=TransactionType.P2P
        )

        self.assertIsNotNone(applicable_fee)
        self.assertIsInstance(applicable_fee, float)
