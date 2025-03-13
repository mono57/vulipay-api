import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.accounts.managers import AccountManager, PhoneNumberManager, UserManager
from app.core.utils import (
    AppCharField,
    AppModel,
    check_pin,
    make_payment_code,
    make_pin,
)


def compute_next_attempt_time(count) -> datetime.datetime:
    dt_now = timezone.now()
    time_diff = dt_now + datetime.timedelta(seconds=30 * count)

    return time_diff


def compute_next_verif_attempt_time(count) -> datetime.datetime:
    dt_now = timezone.now()
    time_diff = dt_now + datetime.timedelta(minutes=10)

    return time_diff


def create_master_account_after_migration():
    Account.objects.create_master_account()


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = AppCharField(
        _("Phone Number"), max_length=20, unique=True, null=True, blank=True
    )
    email = models.EmailField(_("Email address"), unique=True, null=True, blank=True)
    full_name = AppCharField(_("Full name"), max_length=150, null=True, blank=True)
    country = models.ForeignKey(
        "AvailableCountry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text=_("User's country, set during OTP verification"),
    )

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []  # Email is already required as USERNAME_FIELD

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        identifier = self.phone_number or self.email or str(self.id)
        if self.country:
            return f"{identifier} ({self.country.name})"
        return identifier

    def clean(self):
        super().clean()
        if not self.phone_number and not self.email:
            raise ValueError(
                _("User must have either a phone number or an email address")
            )

    def get_full_name(self):
        return self.full_name.strip() if self.full_name else ""

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else ""


class AvailableCountry(AppModel):
    name = AppCharField(max_length=50)  # i.e Chad
    dial_code = AppCharField(max_length=5, unique=True)  # i.e 235
    iso_code = AppCharField(max_length=10, unique=True)  # i.e TD
    phone_number_regex = AppCharField(max_length=50)

    class Meta:
        indexes = [models.Index(fields=["iso_code"])]

    def __str__(self):
        return f"({self.dial_code}) - {self.name} - {self.iso_code}"


class Currency(AppModel):
    iso_code = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} - {self.iso_code} - {self.symbol}"


class Account(AppModel):
    phone_number = AppCharField(_("Phone Number"), max_length=20, null=False)
    intl_phone_number = AppCharField(_("Phone Number"), max_length=20, null=False)
    number = AppCharField(_("Account number"), max_length=16, unique=True, null=False)
    balance = models.FloatField(_("Account balance"), default=0)
    payment_code = AppCharField(
        _("Payment Qr Code"), max_length=255, null=False, blank=True
    )
    owner_email = models.EmailField(
        _("Email address"), unique=True, null=True, blank=True
    )
    owner_first_name = AppCharField(
        _("Firstname"), max_length=50, null=True, blank=True
    )
    owner_last_name = AppCharField(_("Lastname"), max_length=50, null=True, blank=True)
    pin = AppCharField(_("Pin code"), max_length=255, null=True)
    is_active = models.BooleanField(default=True)
    is_master = models.BooleanField(default=False)

    country = models.ForeignKey(
        AvailableCountry, null=True, on_delete=models.SET_NULL, related_name="accounts"
    )

    objects: AccountManager = AccountManager()

    class Meta:
        indexes = [models.Index(fields=["intl_phone_number"])]

    def __str__(self):
        return f"{self.number}"

    def save(self, **kwargs):
        if self.number is None:
            self.number = AccountManager.generate_account_number()
            self.payment_code = make_payment_code(self.number, "CST")
        super().save(**kwargs)

    def set_pin(self, pin):
        self.pin = make_pin(pin)
        self.save()

    def verify_pin(self, raw_pin):
        is_correct = check_pin(self.pin, raw_pin)
        return is_correct

    def set_balance(self, balance):
        self.balance = balance
        self.save()

    def check_balance(self, charged_amount):
        if charged_amount > self.balance:
            return -1
        return 0

    def debit(self, charged_amount):
        balance = self.balance - charged_amount
        self.set_balance(balance)

    def credit(self, amount):
        balance = self.balance + amount
        self.set_balance(balance)

    @classmethod
    def credit_master_account(cls, balance):
        cls.objects.credit_master_account(balance)


class SupportedMobileMoneyCarrier(AppModel):
    name = AppCharField(_("Name"), max_length=254, null=False)
    code = AppCharField(_("Code"), max_length=254, null=False, unique=True)
    country = models.ForeignKey(
        AvailableCountry, on_delete=models.DO_NOTHING, related_name="carriers"
    )
    flag = models.ImageField(_("Flag"))

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        self.code = f"{self.name}_{self.country.iso_code}".lower()
        super().save(**kwargs)


class PhoneNumber(AppModel):
    # National phone number
    # TODO: Variable to be rename to nat_phone_number vs intl_phone_number
    number = AppCharField(max_length=20)
    carrier = models.ForeignKey(
        SupportedMobileMoneyCarrier,
        on_delete=models.DO_NOTHING,
        related_name="phonenumbers",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
        verbose_name=_("Account"),
    )

    objects = PhoneNumberManager()

    def __str__(self):
        return f"({self.country.dial_code}) {self.number}"

    @classmethod
    def create(cls, phone_number: str, carrier_id: int, account_id: int):
        obj = cls.objects.create(
            number=phone_number, account_id=account_id, carrier_id=carrier_id
        )

        return obj
