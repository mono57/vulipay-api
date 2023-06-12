import factory
from factory import Faker as faker
from factory import django

from app.core.utils import make_payment_code, make_transaction_ref
from app.transactions.models import Transaction, TransactionStatus, TransactionType


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
    def create_p2p_transaction(cls, **kwargs):
        return cls.create(
            status=TransactionStatus.PENDING, **kwargs, type=TransactionType.P2P
        )
