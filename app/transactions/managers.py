from django.db import models
from django.db.models import Q

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
    def get_applicable_fee(self, country, transaction_type, payment_method_type):
        fee = (
            (
                self.filter(
                    Q(country=country)
                    & Q(transaction_type=transaction_type)
                    & (
                        Q(payment_method_type=payment_method_type)
                        | Q(payment_method_type__isnull=True)
                    )
                )
            )
            .values("fixed_fee", "percentage_fee")
            .first()
        )

        if fee:
            return fee["fixed_fee"], fee["percentage_fee"]
        return 0, 0


class WalletManager(models.Manager):
    def get_user_main_wallet(self, user):
        from app.transactions.models import WalletType

        return self.filter(user=user, wallet_type=WalletType.MAIN).first()


class PlatformWalletManager(models.Manager):
    def collect_fees(self, country, amount):
        self.filter(country=country).update(balance=models.F("balance") + amount)
