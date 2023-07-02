from django.db import models

from app.core.utils import make_payment_code, make_transaction_ref


class TransactionManager(models.Manager):
    def _create(self, type: str, **kwargs):
        transaction_ref = make_transaction_ref(type)
        t_payment_code = make_payment_code(transaction_ref, type)

        kwargs.setdefault("reference", transaction_ref)
        kwargs.setdefault("payment_code", t_payment_code)

        transaction = self.create(type=type, **kwargs)

        return transaction


class TransactionFeeManager(models.Manager):
    def get_applicable_fee(self, country, transaction_type):
        t_fee = (
            self.filter(country=country, transaction_type=transaction_type)
            .values("fee")
            .first()
        )
        return t_fee["fee"]
