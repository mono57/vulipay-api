from unittest.mock import patch

from django.test import TestCase

from app.accounts.models import Account
from app.accounts.tests import factories as f
from app.transactions.api import serializers as t_serializers
from app.transactions.models import Transaction


class BaseTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = t_serializers.BaseTransactionSerializer

    def test_it_should_not_validate_for_wrong_amount(self):
        data = {"amount": 0}
        serializer = self.serializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

        data["amount"] = -200

        serializer = self.serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class P2PTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = t_serializers.P2PTransactionSerializer

    def test_it_should_not_validate_if_body_empty(self):
        serializer = self.serializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_it_should_validate_serializer(self):
        data = {"amount": 30}
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())


class TransactionDetailsSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer = t_serializers.TransactionDetailsSerializer
        self.receiver_account = f.AccountFactory.create()
        self.transaction = Transaction.create_P2P_transaction(
            2000, receiver_account=self.receiver_account
        )

    def test_it_should_serialize_P2P_transaction(self):
        serializer = self.serializer(self.transaction)

        data = serializer.data

        self.assertIn("payer_account", data)
        self.assertIsNotNone(data.get("reference"))
        self.assertIsNotNone(data.get("status"))
        self.assertIsNotNone(data.get("type"))
        self.assertIsNotNone(data.get("amount"))
        self.assertIsNotNone(data.get("receiver_account"))


class MPTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = t_serializers.MPTransactionSerializer
        self.receiver_account: Account = f.AccountFactory.create()
        self.fake_amount = float(2000)

    def test_it_should_not_validate_transaction_for_not_existing_account(self):
        data = {"amount": self.fake_amount, "receiver_account": "23542"}
        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("receiver_account", s.errors)

    def test_it_should_validate_transaction(self):
        data = {
            "amount": self.fake_amount,
            "receiver_account": self.receiver_account.number,
        }

        s = self.serializer(data=data)
        self.assertTrue(s.is_valid())

    def test_it_should_create_MP_transaction(self):
        payer_account = f.AccountFactory.create(
            phone_number="698238382", country=self.receiver_account.country
        )
        data = {
            "amount": self.fake_amount,
            "receiver_account": self.receiver_account.number,
        }
        s = self.serializer(data=data)
        s.is_valid()

        with patch(
            "app.transactions.models.Transaction.create_MP_transaction"
        ) as mocked_create_MP_transaction:
            validated_data = {
                **data,
                "receiver_account": self.receiver_account,
                "payer_account": payer_account,
            }
            s.create(validated_data)

            mocked_create_MP_transaction.assert_called_once_with(
                amount=self.fake_amount,
                receiver_account=self.receiver_account,
                payer_account=payer_account,
            )
