from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from app.accounts.models import Account, AvailableCountry, PhoneNumber, User
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
    CashIn = "CI", _("Cash In")
    CashOut = "CO", _("Cash Out")


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
    from_phone_number = models.ForeignKey(
        PhoneNumber,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cashin_transations",
    )
    to_account = models.ForeignKey(
        Account,
        null=True,
        on_delete=models.SET_NULL,
        related_name="cashin_transactions",
    )
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
        transaction = cls.objects._create(
            type=TransactionType.CashOut,
            amount=amount,
            from_account=from_account,
            to_phone_number=to_phone_number,
            status=TransactionStatus.PENDING,
        )

        return transaction

    @classmethod
    def create_CI_transaction(cls, amount, to_account, from_phone_number):
        transaction = cls.objects._create(
            type=TransactionType.CashIn,
            amount=amount,
            to_account=to_account,
            from_phone_number=from_phone_number,
            status=TransactionStatus.PENDING,
        )

        return transaction

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


class PaymentMethod(AppModel):
    PAYMENT_TYPE_CHOICES = (
        ("card", "Card"),
        ("mobile_money", "Mobile Money"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payment_methods",
        help_text=_("User who owns this payment method"),
    )
    type = models.CharField(
        max_length=50,
        choices=PAYMENT_TYPE_CHOICES,
        help_text=_("Type of payment method (card or mobile money)"),
    )
    default_method = models.BooleanField(
        default=False,
        help_text=_("Whether this is the default payment method for the user"),
    )

    cardholder_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Name of the cardholder (for card payment methods)"),
    )
    masked_card_number = models.CharField(
        max_length=19,
        null=True,
        blank=True,
        help_text=_(
            "Masked card number, e.g., **** **** **** 1234 (for card payment methods)"
        ),
    )
    expiry_date = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        help_text=_("Card expiry date in MM/YYYY format (for card payment methods)"),
    )
    cvv_hash = models.TextField(
        null=True,
        blank=True,
        help_text=_("Hashed CVV (not plaintext) for card payment methods"),
    )
    billing_address = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Billing address associated with the card (for card payment methods)"
        ),
    )

    # Mobile Money Fields (Only for 'mobile_money' type)
    provider = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_(
            "Mobile money provider, e.g., M-Pesa, MTN Mobile Money (for mobile money payment methods)"
        ),
    )
    mobile_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_(
            "Mobile number associated with the mobile money account (for mobile money payment methods)"
        ),
    )
    account_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=_(
            "Name associated with the mobile money account (for mobile money payment methods)"
        ),
    )

    class Meta:
        verbose_name = _("payment method")
        verbose_name_plural = _("payment methods")

    def __str__(self):
        if self.type == "card":
            return f"Card: {self.masked_card_number}"
        else:
            return f"Mobile Money: {self.provider} - {self.mobile_number}"

    def save(self, *args, **kwargs):
        if self.default_method:
            PaymentMethod.objects.filter(user=self.user, default_method=True).update(
                default_method=False
            )

        if not self.pk and not PaymentMethod.objects.filter(user=self.user).exists():
            self.default_method = True

        super().save(*args, **kwargs)
