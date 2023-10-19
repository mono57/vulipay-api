from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from app.accounts.models import Account, AvailableCountry, PhoneNumber
from app.core.utils import (
    AppCharField,
    AppModel,
    is_valid_payment_code,
    make_payment_code,
    make_transaction_ref,
)
from app.transactions import managers
from app.transactions.managers import TransactionFeeManager
from app.transactions.utils import compute_inclusive_amount


class TransactionStatus(models.TextChoices):
    INITIATED = "INITIATED", _("Initiated")
    PENDING = "PENDING", _("Pending")
    SUCCEED = "SUCCEED", _("Succeed")
    COMPLETED = "COMPLETED", ("Completed")
    FAILED = "FAILED", _("Failed")


class TransactionType(models.TextChoices):
    P2P = "P2P", _("Peer to Peer")
    MP = "MP", _("Merchant payment")
    CI = "CI", _("Cash In")
    CO = "CO", _("Cash Out")


class TransactionFee(AppModel):
    fee = models.FloatField()
    country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)
    transaction_type = AppCharField(
        _("Transaction Type"), max_length=10, choices=TransactionType.choices
    )

    objects = TransactionFeeManager()

    def __str__(self):
        return self.fee


class Transaction(AppModel):
    reference = AppCharField(_("Reference"), max_length=30)
    payment_code = AppCharField(_("Payment code"), max_length=255)
    amount = models.FloatField(_("Amount"))
    charged_amount = models.FloatField(_("Charged Amount"), null=True)
    calculated_fee = models.FloatField(_("Calculated Fee"), null=True)
    status = AppCharField(_("Status"), max_length=10, choices=TransactionStatus.choices)
    type = AppCharField(_("Type"), max_length=4, choices=TransactionType.choices)
    payer_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, related_name="debit_transactions"
    )
    receiver_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name="credit_transactions",
    )
    from_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cashout_transactions",
    )
    to_phone_number = models.ForeignKey(
        PhoneNumber,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cashout_transations",
    )
    # from_phone_number = AppCharField(max_length=30, null=True)
    # to_account = models.ForeignKey(Account, on_delete=models.SET_NULL, related_name="cashin_transactions")
    notes = models.TextField(_("Notes"), null=True)

    objects = managers.TransactionManager()

    def __str__(self):
        return self.reference

    @classmethod
    def is_valid_payment_code(cls, payment_code):
        return is_valid_payment_code(payment_code, TransactionType.values)

    @classmethod
    def create_P2P_transaction(
        cls, amount: float, receiver_account: Account, notes: str = None
    ):
        transaction = cls.objects._create(
            type=TransactionType.P2P,
            amount=amount,
            receiver_account=receiver_account,
            status=TransactionStatus.INITIATED,
            notes=notes,
        )

        return transaction

    @classmethod
    def create_MP_transaction(
        cls,
        amount: float,
        receiver_account,
        payer_account,
        notes: str = None,
    ):
        mp_transaction = cls.objects._create(
            type=TransactionType.MP,
            amount=amount,
            receiver_account=receiver_account,
            payer_account=payer_account,
            status=TransactionStatus.PENDING,
            notes=notes,
        )

        return mp_transaction

    @classmethod
    def create_CO_transaction(cls, amount, from_account, to_phone_number):
        co_transaction = cls.objects._create(
            type=TransactionType.CO,
            amount=amount,
            from_account=from_account,
            to_phone_number=to_phone_number,
            status=TransactionStatus.PENDING,
        )

        return co_transaction

    def get_inclusive_amount(self, country):
        if self.charged_amount is not None and self.calculated_fee is not None:
            return self.charged_amount

        fee = TransactionFee.objects.get_applicable_fee(
            country=country, transaction_type=self.type
        )
        self.calculated_fee, self.charged_amount = compute_inclusive_amount(
            self.amount, fee
        )

        self.save()

        return self.charged_amount

    def _set_status(self, status_code):
        self.status = status_code

    def set_as_PENDING(self):
        self._set_status(TransactionStatus.PENDING)

    def set_as_COMPLETED(self):
        self._set_status(TransactionStatus.COMPLETED)
        self.save()

    def pair(self, payer_account):
        self.payer_account = payer_account
        self.set_as_PENDING()
        self.save()

    def is_status_allowed(self, status):
        return self.status == status

    @transaction.atomic()
    def perform_payment(self):
        self.payer_account.debit(self.charged_amount)
        self.receiver_account.credit(self.amount)
        Account.credit_master_account(self.calculated_fee)
        self.set_as_COMPLETED()
