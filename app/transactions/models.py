from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.accounts.models import AvailableCountry
from app.core.utils import AppCharField, AppModel, is_valid_payment_code
from app.transactions import managers
from app.transactions.managers import TransactionFeeManager
from app.transactions.utils import compute_inclusive_amount

User = get_user_model()


class TransactionStatus(models.TextChoices):
    INITIATED = "INITIATED", _("Initiated")
    PENDING = "PENDING", _("Pending")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")
    CANCELLED = "CANCELLED", _("Cancelled")


class TransactionType(models.TextChoices):
    P2P = "P2P", _("Peer to Peer")
    MP = "MP", _("Merchant Payment")
    CashOut = "CO", _("Cash Out")
    CashIn = "CI", _("Cash In")


class PaymentMethodType(AppModel):
    name = AppCharField(_("Name"), max_length=255)
    code = AppCharField(_("Code"), max_length=255)
    cash_in_transaction_fee = models.FloatField(_("Cash In Transaction Fee"), null=True)
    cash_out_transaction_fee = models.FloatField(
        _("Cash Out Transaction Fee"), null=True
    )
    country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _("Payment Method Type")
        verbose_name_plural = _("Payment Method Types")

    def __str__(self):
        return self.name


class TransactionFee(AppModel):
    class FeePriority(models.TextChoices):
        FIXED = "fixed", _("Fixed Fee")
        PERCENTAGE = "percentage", _("Percentage Fee")
        BOTH = "both", _("Both")

    fixed_fee = models.FloatField(null=True, db_index=True)  # i.e: 100
    percentage_fee = models.FloatField(null=True, db_index=True)  # i.e: 5
    fee_priority = models.CharField(
        max_length=20, choices=FeePriority.choices, default=FeePriority.PERCENTAGE
    )
    country = models.ForeignKey(
        AvailableCountry, null=True, on_delete=models.SET_NULL, db_index=True
    )
    payment_method_type = models.ForeignKey(
        PaymentMethodType,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transaction_fees",
        help_text=_("Payment method type associated with this fee"),
        db_index=True,
    )
    transaction_type = AppCharField(
        _("Transaction Type"),
        max_length=10,
        choices=TransactionType.choices,
        db_index=True,
    )

    objects = TransactionFeeManager()

    class Meta:
        verbose_name = _("Transaction Fee")
        verbose_name_plural = _("Transaction Fees")
        indexes = [
            models.Index(
                fields=["country", "transaction_type", "payment_method_type"],
                name="tx_fee_lookup_idx",
            ),
            models.Index(fields=["transaction_type"], name="tx_fee_type_idx"),
        ]
        unique_together = [["country", "transaction_type", "payment_method_type"]]

    @classmethod
    def get_inclusive_amount(cls, transaction_type, country):
        try:
            transaction_fee = cls.objects.select_related(
                "country", "payment_method_type"
            ).get(transaction_type=transaction_type, country=country)
            return transaction_fee.fee
        except cls.DoesNotExist:
            return 0

    @property
    def fee(self):
        if self.fee_priority == self.FeePriority.FIXED:
            return self.fixed_fee or 0
        elif self.fee_priority == self.FeePriority.PERCENTAGE:
            return self.percentage_fee or 0
        elif self.fee_priority == self.FeePriority.BOTH:
            return (self.fixed_fee or 0, self.percentage_fee or 0)
        return 0

    def __str__(self):
        country_name = self.country.name if self.country else "Global"
        payment_type = (
            self.payment_method_type.name if self.payment_method_type else "All"
        )

        if self.fee_priority == self.FeePriority.FIXED:
            fee_info = f"Fixed: {self.fixed_fee}"
        elif self.fee_priority == self.FeePriority.PERCENTAGE:
            fee_info = f"Percentage: {self.percentage_fee}%"
        else:
            fee_info = f"Fixed: {self.fixed_fee}, Percentage: {self.percentage_fee}%"

        return f"{country_name} - {self.transaction_type} - {payment_type} - {fee_info}"


class Transaction(AppModel):
    reference = AppCharField(_("Reference"), max_length=30)
    amount = models.FloatField(_("Amount"))
    charged_amount = models.FloatField(_("Charged Amount"), null=True)
    calculated_fee = models.FloatField(_("Calculated Fee"), null=True)
    status = AppCharField(_("Status"), max_length=10, choices=TransactionStatus.choices)
    type = AppCharField(_("Type"), max_length=4, choices=TransactionType.choices)
    payment_method = models.ForeignKey(
        "PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
        help_text=_("Payment method used for the transaction"),
    )
    from_wallet = models.ForeignKey(
        "Wallet",
        on_delete=models.SET_NULL,
        null=True,
        related_name="outgoing_transactions",
        help_text=_("Wallet that sent the transaction"),
    )
    to_wallet = models.ForeignKey(
        "Wallet",
        on_delete=models.SET_NULL,
        null=True,
        related_name="incoming_transactions",
        help_text=_("Wallet that received the transaction"),
    )
    notes = models.TextField(_("Notes"), null=True)

    objects = managers.TransactionManager()

    def __str__(self):
        return self.reference

    @classmethod
    def create_transaction(
        cls,
        transaction_type,
        amount,
        status=TransactionStatus.INITIATED,
        **kwargs,
    ):
        from app.core.utils.hashers import make_transaction_ref

        transaction = cls.objects.create(
            reference=make_transaction_ref(transaction_type),
            amount=amount,
            status=status,
            type=transaction_type,
            from_wallet=kwargs.get("source_wallet"),
            to_wallet=kwargs.get("target_wallet"),
            payment_method=kwargs.get("payment_method"),
            notes=kwargs.get("notes"),
            calculated_fee=kwargs.get("calculated_fee"),
            charged_amount=kwargs.get("charged_amount"),
        )

        return transaction

    @classmethod
    def is_valid_payment_code(cls, payment_code):
        return is_valid_payment_code(payment_code, TransactionType.values)

    def get_inclusive_amount(self, country):
        if self.charged_amount is not None and self.calculated_fee is not None:
            return self.charged_amount

        payment_method_type = None
        if self.payment_method and hasattr(self.payment_method, "payment_method_type"):
            payment_method_type = self.payment_method.payment_method_type

        fixed_fee, percentage_fee = TransactionFee.objects.get_applicable_fee(
            country=country,
            transaction_type=self.type,
            payment_method_type=payment_method_type,
        )

        if fixed_fee is not None and percentage_fee is not None:
            percentage_amount = (self.amount * percentage_fee) / 100
            self.calculated_fee = fixed_fee + percentage_amount
            self.charged_amount = self.amount + self.calculated_fee
        elif fixed_fee is not None:
            self.calculated_fee = fixed_fee
            self.charged_amount = self.amount + fixed_fee
        elif percentage_fee is not None:
            self.calculated_fee = (self.amount * percentage_fee) / 100
            self.charged_amount = self.amount + self.calculated_fee
        else:
            self.calculated_fee = 0
            self.charged_amount = self.amount

        self.save(update_fields=["calculated_fee", "charged_amount"])

        return self.charged_amount

    def _set_status(self, status_code):
        self.status = status_code

    def set_as_PENDING(self):
        self._set_status(TransactionStatus.PENDING)

    def set_as_COMPLETED(self):
        self._set_status(TransactionStatus.COMPLETED)
        self.save()


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
    payment_method_type = models.ForeignKey(
        PaymentMethodType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_methods",
        help_text=_(
            "The specific type of payment method (e.g., Visa, Mastercard, MTN Mobile Money)"
        ),
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


class WalletType(models.TextChoices):
    MAIN = "MAIN", _("Main Wallet")
    BUSINESS = "BUSINESS", _("Business Wallet")


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallets")
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Current wallet balance"),
    )
    wallet_type = AppCharField(
        _("Wallet Type"),
        max_length=10,
        choices=WalletType.choices,
        default=WalletType.MAIN,
        help_text=_("Type of wallet (Main or Business)"),
    )
    currency = AppCharField(
        _("Currency"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Currency for this wallet (e.g., USD, EUR, XAF)"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True, help_text=_("Whether this wallet is active")
    )

    objects = managers.WalletManager()

    class Meta:
        unique_together = ["user", "wallet_type"]
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")

    def __str__(self):
        currency_str = f" ({self.currency})" if self.currency else ""
        return f"{self.user.email}'s {self.get_wallet_type_display()}{currency_str}"

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError(_("Deposit amount must be positive"))

        from decimal import Decimal

        self.balance += Decimal(str(amount))
        self.save()
        return self.balance

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError(_("Withdrawal amount must be positive"))

        if amount > self.balance:
            raise ValueError(_("Insufficient funds"))

        self.balance -= amount
        self.save()
        return self.balance

    def transfer(self, destination_wallet, amount):
        if amount <= 0:
            raise ValueError(_("Transfer amount must be positive"))

        if amount > self.balance:
            raise ValueError(_("Insufficient funds"))

        self.balance -= amount
        destination_wallet.balance += amount

        self.save()
        destination_wallet.save()

        return True

    def save(self, *args, **kwargs):
        if self.user and self.user.country and hasattr(self.user.country, "currency"):
            self.currency = self.user.country.currency
        super().save(*args, **kwargs)


class PlatformWallet(AppModel):
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Current wallet balance"),
    )
    currency = AppCharField(
        _("Currency"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Currency for this wallet (e.g., USD, EUR, XAF)"),
    )

    country = models.ForeignKey(
        AvailableCountry, on_delete=models.SET_NULL, null=True, blank=True
    )

    objects = managers.PlatformWalletManager()

    def __str__(self):
        return f"Platform Wallet ({self.currency})"
