import factory
from factory import Faker as faker
from factory import django

from app.accounts.tests.factories import AvailableCountryFactory
from app.core.utils import make_payment_code, make_transaction_ref
from app.transactions.models import (
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
)


class TransactionFactory(django.DjangoModelFactory):
    class Meta:
        model = Transaction

    amount = 2000

    @classmethod
    def create(cls, **kwargs):
        transaction_ref = make_transaction_ref(kwargs.get("type"))
        t_payment_code = make_payment_code(transaction_ref, kwargs.get("type"))

        return super().create(
            reference=transaction_ref, payment_code=t_payment_code, **kwargs
        )

    @classmethod
    def create_p2p_transaction(cls, receiver_account, **kwargs):
        status = kwargs.pop("status", TransactionStatus.INITIATED)

        return cls.create(
            status=status,
            receiver_account=receiver_account,
            **kwargs,
            type=TransactionType.P2P
        )

    @classmethod
    def create_pending_transaction(cls, receiver_account, payer_account, **kwargs):
        return cls.create(
            status=TransactionStatus.PENDING,
            type=TransactionType.P2P,
            receiver_account=receiver_account,
            payer_account=payer_account,
            amount=2000,
            calculated_fee=40,
            charged_amount=2040,
            **kwargs
        )


class TransactionFeeFactory(django.DjangoModelFactory):
    class Meta:
        model = TransactionFee

    fee = 2
    country = factory.SubFactory(AvailableCountryFactory)

    @classmethod
    def create_p2p_transaction_fee(cls, **kwargs):
        return cls.create(**kwargs, transaction_type=TransactionType.P2P)
