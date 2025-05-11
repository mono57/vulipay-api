from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

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
    def get_applicable_fee(
        self,
        country,
        transaction_type,
        payment_method_type=None,
        payment_method_type_id=None,
    ):
        country_id = getattr(country, "id", country)

        if payment_method_type_id is None and payment_method_type is not None:
            payment_method_type_id = getattr(
                payment_method_type, "id", payment_method_type
            )

        cache_key = (
            f"transaction_fee:{country_id}:{transaction_type}:{payment_method_type_id}"
        )
        cached_fee = cache.get(cache_key)

        if cached_fee is not None:
            return cached_fee

        query = Q(transaction_type=transaction_type)

        if country:
            query &= Q(country_id=country_id) | Q(country__isnull=True)
        else:
            query &= Q(country__isnull=True)

        if payment_method_type_id:
            query &= Q(payment_method_type_id=payment_method_type_id) | Q(
                payment_method_type__isnull=True
            )
        else:
            query &= Q(payment_method_type__isnull=True)

        # Order by specificity (most specific first)
        # Both country and payment_method_type specified is most specific
        # Only one specified is less specific
        # Neither specified is least specific
        # Also prioritize fixed fees over percentage fees
        fee = (
            self.filter(query)
            .extra(
                select={
                    "specificity": """
                    CASE
                        WHEN country_id IS NOT NULL AND payment_method_type_id IS NOT NULL THEN 3
                        WHEN country_id IS NOT NULL THEN 2
                        WHEN payment_method_type_id IS NOT NULL THEN 1
                        ELSE 0
                    END
                    """
                },
                order_by=["-specificity"],
            )
            .first()
        )

        if fee:
            fee_value = fee.fee
            cache.set(cache_key, fee_value, timeout=3600)
            return fee_value
        else:
            cache.set(cache_key, 0, timeout=3600)
            return 0


class WalletManager(models.Manager):
    def get_user_main_wallet(self, user):
        from app.transactions.models import WalletType

        return self.filter(user=user, wallet_type=WalletType.MAIN).first()

    def get_wallet(self, wallet_id, user):
        try:
            return self.get(id=wallet_id, user=user)
        except self.model.DoesNotExist:
            return None


class PlatformWalletManager(models.Manager):
    def collect_fees(self, country, amount):
        self.filter(country=country).update(balance=models.F("balance") + amount)
