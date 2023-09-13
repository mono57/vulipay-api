import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.accounts.managers import AccountManager, PassCodeManager
from app.core.utils import (
    AppCharField,
    AppModel,
    MessageClient,
    check_pin,
    get_carrier,
    make_otp,
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


class PassCode(AppModel):
    intl_phone_number = AppCharField(max_length=15, null=False)
    code = AppCharField(max_length=8, null=False)
    sent_on = models.DateTimeField(null=True)
    verified = models.BooleanField(default=False)
    expired = models.BooleanField(default=False)
    next_passcode_on = models.DateTimeField(null=False)
    next_verif_attempt_on = models.DateTimeField(null=False)
    last_attempt_on = models.DateTimeField(null=True)
    attempt_count = models.IntegerField(default=0)
    passcode_count = models.IntegerField(default=1)

    objects = PassCodeManager()

    class Meta:
        indexes = [models.Index(fields=["intl_phone_number"])]

    def __str__(self):
        return self.code

    @property
    def key_expired(self):
        if self.expired:
            return True

        sent_threshold = self.sent_on + datetime.timedelta(
            seconds=settings.OTP_TIMESTAMP
        )

        return sent_threshold < timezone.now()

    @property
    def is_verified(self):
        return self.verified

    @classmethod
    def create(cls, intl_phone_number):
        last_code: cls = cls.objects.get_last_code(intl_phone_number)

        passcode_count = 1
        next_passcode_on = compute_next_attempt_time(passcode_count)

        if last_code and not last_code.is_verified:
            last_code.set_expired()
            passcode_count = last_code.passcode_count + 1
            next_passcode_on = compute_next_attempt_time(passcode_count)

        code = make_otp()

        code = cls._default_manager.create(
            intl_phone_number=intl_phone_number,
            next_verif_attempt_on=timezone.now(),
            next_passcode_on=next_passcode_on,
            passcode_count=passcode_count,
            code=code,
        )

        code.send_code()

        return code

    def verify(self, code):
        matched = self.code == code

        if not matched:
            self.increate_next_attempt_time()
        else:
            self.set_verified()

        return matched

    def increate_next_attempt_time(self):
        verif_attempt_count = self.attempt_count + 1
        next_verif_attempt_on = compute_next_verif_attempt_time(verif_attempt_count)

        self.last_attempt_on = timezone.now()
        self.next_passcode_on = next_verif_attempt_on
        self.next_verif_attempt_on = next_verif_attempt_on
        self.attempt_count = verif_attempt_count

        self.save()

    def set_verified(self, is_verified=True):
        self.verified = is_verified
        self.expired = is_verified
        self.save()

    def set_expired(self):
        self.expired = True
        self.save()

    def send_code(self):
        body = MessageClient._BODY_VIRIFICATION.format(self.code)
        MessageClient.send_message(body, self.intl_phone_number)
        self.sent_on = datetime.datetime.now(timezone.utc)

        self.save()


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
    number = AppCharField(max_length=20)
    primary = models.BooleanField(default=False)
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

    def __str__(self):
        return f"({self.country.dial_code}) {self.number}"

    @classmethod
    def create(cls, phone_number: str, carrier_id: int, account_id: int):
        obj = cls.objects.create(
            number=phone_number, account_id=account_id, carrier_id=carrier_id
        )

        return obj
