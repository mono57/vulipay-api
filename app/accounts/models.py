import datetime

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

from app.core.utils import MessageClient, generate_code, AppModel, AppCharField, get_carrier
from accounts.crypto import Hasher
from app.accounts.managers import PhoneNumberManager, AccountManager, AvailableCountryManager, PassCodeManager

def increase_waiting_time(waiting_time):
    # compute waiting time base on mathematic formula
    return waiting_time + 30

class AvailableCountry(AppModel):
    name = AppCharField(max_length=30)  # i.e Chad
    dial_code = AppCharField(max_length=5, unique=True)  # i.e 235
    iso_code = AppCharField(max_length=10, unique=True)  # i.e TD
    phone_number_regex = AppCharField(max_length=50)

    objects = AvailableCountryManager()

    def __str__(self):
        return f"({self.dial_code}) - {self.name} - {self.iso_code}"


# class Currency(AppModel):
#     iso_code = models.CharField(max_length=8)
#     name = models.CharField(max_length=100)
#     symbol = models.CharField(max_length=5)
#     country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)

#     def __str__(self):
#         return f"{self.name} - {self.iso_code} - {self.symbol}"


class PassCode(AppModel):
    phone_number = AppCharField(max_length=20)
    country_iso_code = AppCharField(max_length=2)
    code = AppCharField(max_length=8)
    sent_date = models.DateTimeField(null=True)
    verified = models.BooleanField(default=False)
    expired = models.BooleanField(default=False)
    waiting_time = models.IntegerField(default=30)  # waiting time to send new code
    next_attempt_on = models.DateTimeField(auto_now_add=True)
    last_attempt_on = models.DateTimeField(null=True)
    attempt_count = models.IntegerField(default=0)

    objects = PassCodeManager()

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'country_iso_code'])
        ]

    def __str__(self):
        return self.code

    @property
    def key_expired(self):
        if self.expired or self.verified:
            return True

        expiration_date = self.sent_date + datetime.timedelta(
            seconds=self.waiting_time
        )

        return expiration_date < timezone.now()

    # def check_can_verify(self):
    #     if self.last_attempt_on is None and self.attempt_count == 0 or self.verified:
    #         return True

    #     is_expired = self.is_time_expired_for(self.last_attempt_on, self.next_attempt_on)

    #     return is_expired

    @property
    def is_verified(self):
        return self.verified

    @classmethod
    def create(cls, phone_number, country_iso_code):
        last_code: cls = cls.objects.get_last_code(phone_number, country_iso_code)

        if last_code and not last_code.is_verified and not last_code.is_time_expired_for(
            last_code.sent_date,
            last_code.waiting_time):
            return last_code

        waiting_time = settings.DEFAULT_WAITING_TIME_SECONDS

        if last_code and not last_code.is_verified and last_code.is_time_expired_for(
            last_code.sent_date,
            last_code.waiting_time):
            last_code.set_expired()
            waiting_time = increase_waiting_time(last_code.waiting_time)

        code = generate_code(cls)

        code = cls._default_manager.create(
            phone_number=phone_number,
            country_iso_code=country_iso_code,
            waiting_time=waiting_time,
            code=code)

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
        dt_now = datetime.datetime.now(timezone.utc)

        self.last_attempt_on = dt_now
        self.next_attempt_on = dt_now + datetime.timedelta(seconds=30)
        self.attempt_count = self.attempt_count + 1
        self.save()

    def get_remaining_time(self, target_date, time_to_wait):
        time_threshold = target_date.timestamp() + time_to_wait
        dt_now = datetime.datetime.now(timezone.utc)

        remaining_time = time_threshold - dt_now.timestamp()

        return remaining_time

    def is_time_expired_for(self, target_date, time_to_wait):
        rt = self.get_remaining_time(target_date, time_to_wait)

        return rt <= 0

    def set_verified(self, is_verified=True):
        self.verified = is_verified
        self.save()

    def set_expired(self):
        self.expired = True
        self.save()

    def send_code(self):
        body = MessageClient._BODY_VIRIFICATION.format(self.code)

        MessageClient.send_message(body, self.phone_number)

        self.sent_date = datetime.datetime.now(timezone.utc)

        self.save()


class Account(AppModel):
    number = AppCharField(_('Account number'), max_length=16, unique=True, null=False)
    payment_code = AppCharField(_('Payment Qr Code'), max_length=255, null=False, blank=True)
    owner_email = models.EmailField(_("Email address"), unique=True, null=True, blank=True)
    owner_first_name = AppCharField(_("Firstname"), max_length=50, null=True, blank=True)
    owner_last_name = AppCharField(_("Lastname"), max_length=50, null=True, blank=True)

    is_active = models.BooleanField(default=False)


    objects: AccountManager = AccountManager()

    def __str__(self):
        return self.email

    def save(self, **kwargs):
        if self.number is None:
            self.number = AccountManager.generate_account_number()
            self.payment_code = Hasher.hash(self.number)
        super().save(**kwargs)


class PhoneNumber(AppModel):
    number = AppCharField(max_length=20)
    primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    carrier = AppCharField(_("Carrier"), max_length=50)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
        verbose_name=_("Account"),
    )
    country = models.ForeignKey(
        AvailableCountry,
        on_delete=models.CASCADE,
        related_name="phone_numbers")

    objects = PhoneNumberManager()

    def __str__(self):
        return f"({self.country.dial_code}) {self.number}"

    @property
    def is_primary(self):
        return self.is_verified and self.primary

    @property
    def is_verified(self):
        return self.verified

    @classmethod
    def create(cls, phone_number: str, country_iso_code: str, verified=True):
        country_id = AvailableCountry.objects.values('id') \
            .get(iso_code=country_iso_code) \
            .get('id')

        account = Account.objects.create()

        carrier = get_carrier(phone_number, country_iso_code)

        obj = cls.objects.create(
            number=phone_number,
            account_id=account.id,
            country_id=country_id,
            carrier=carrier,
            verified=verified)

        return obj

    def set_primary(self):
        self.primary = True
        self.save()
