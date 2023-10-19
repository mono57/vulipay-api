from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from rest_framework import exceptions

from app.accounts.models import Account
from app.accounts.tests.factories import *
from app.transactions.api import serializers
from app.transactions.models import Transaction
from app.transactions.tests.factories import TransactionFactory, TransactionFeeFactory


class BaseTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.BasePaymentTransactionSerializer

    def test_it_should_not_validate_for_wrong_amount(self):
        data = {"amount": 0}
        serializer = self.serializer(data=data)

        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("amount", serializer.errors)

        data["amount"] = -200

        serializer = self.serializer(data=data)
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn("amount", serializer.errors)


class P2PTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.P2PTransactionSerializer

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
        self.serializer = serializers.TransactionDetailsSerializer
        self.receiver_account = AccountFactory.create()
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
        self.assertIn("charged_amount", data)
        self.assertIn("calculated_fee", data)


class MPTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = serializers.MPTransactionSerializer
        self.receiver_account: Account = AccountFactory.create()
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
        payer_account = AccountFactory.create(
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


class CashOutTransactionSerializerTestCase(TransactionTestCase):
    def setUp(self) -> None:
        self.account: Account = AccountFactory.create(balance=10000)
        self.country = self.account.country
        carrier = CarrierFactory.create(country=self.country)
        PhoneNumberFactory.create(account=self.account, carrier=carrier)

    def test_it_should_validate(self):
        payload = {"to_phone_number": "698049741", "amount": 5000, "pin": "2324"}
        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )
        self.assertTrue(s.is_valid())

    def test_it_should_raise_un_verified_phone_number(self):
        payload = {"to_phone_number": "698049742", "amount": 5000, "pin": "2324"}
        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )
        self.assertFalse(s.is_valid())

    def test_it_should_raise_insufficient_balance(self):
        TransactionFeeFactory.create_co_transaction_fee(country=self.country)
        payload = {"to_phone_number": "698049741", "amount": 10000, "pin": "2324"}

        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )

        assert s.is_valid() == True

        validated_data = {**payload}

        with self.assertRaises(exceptions.PermissionDenied):
            s.create(validated_data)

    def test_it_should_initiate_co_transaction(self):
        TransactionFeeFactory.create_co_transaction_fee(country=self.country)
        payload = {"to_phone_number": "698049741", "amount": 5000, "pin": "2324"}

        s = serializers.CashOutTransactionSerializer(
            data=payload, context={"account": self.account}
        )

        assert s.is_valid() == True

        validated_data = {**payload}

        tx = s.create(validated_data)

        self.assertIsInstance(tx, Transaction)
