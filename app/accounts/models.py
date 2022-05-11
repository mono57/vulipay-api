import datetime

from accounts.managers import (AvailableCountryManager,
                               PhoneNumberConfirmationCodeManager, UserManager)
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.utils.generate_code import generate_code
from app.utils.timestamp import TimestampModel
from app.utils.twilio_client import MessageClient


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("Email address"), unique=True, blank=True)
    phone_number = models.CharField(_("Phone number"), max_length=20)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @classmethod
    def get_or_create(cls, phone_number, country_iso_code):

        user, created = cls.objects.get_or_create(phone_number=phone_number)

        if not created:
            return user

        PhoneNumber.create(
            phone_number=phone_number,
            user=user,
            country_iso_code=country_iso_code,
            verified=True,
        )

        return user


class AvailableCountry(TimestampModel):
    name = models.CharField(max_length=30)  # i.e Chad
    calling_code = models.CharField(max_length=5, unique=True)  # i.e 235
    iso_code = models.CharField(max_length=10, unique=True)  # i.e TD
    phone_number_regex = models.CharField(max_length=50)

    objects = AvailableCountryManager()

    def __str__(self):
        return f"({self.calling_code}) - {self.name} - {self.iso_code}"


class Currency(TimestampModel):
    iso_code = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.iso_code, self.symbol)


class NetworkProvider(TimestampModel):
    name = models.CharField(max_length=30, verbose_name=_("name"))

    def __str__(self):
        return self.name


class PhoneNumber(TimestampModel):
    number = models.CharField(max_length=20)
    primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    provider = models.ForeignKey(
        NetworkProvider, blank=True, null=True, on_delete=models.SET_NULL
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
        verbose_name=_("User"),
    )
    country = models.ForeignKey(
        AvailableCountry, on_delete=models.CASCADE, related_name="phone_numbers"
    )

    def __str__(self):
        return f"({self.country.calling_code}) {self.number}"

    @classmethod
    def create(
        cls, phone_number: str, user: User, country_iso_code: str, verified=False
    ):
        country = AvailableCountry.objects.get(iso_code=country_iso_code)

        obj = cls.objects.create(
            number=phone_number, user=user, country=country, verified=verified
        )

        return obj


class PhoneNumberConfirmationCode(TimestampModel):
    phone_number = models.CharField(max_length=20)
    key = models.CharField(max_length=8)
    sent = models.DateTimeField(null=True)
    verified = models.BooleanField(default=False)
    waiting_time = models.IntegerField(default=30)  # waiting time to send new code

    objects = PhoneNumberConfirmationCodeManager()

    def __str__(self):
        return self.key

    @property
    def key_expired(self):
        if self.verified:
            return True

        expiration_date = self.sent + datetime.timedelta(days=settings.CODE_EXPIRE_DAYS)

        return expiration_date <= timezone.now()

    @classmethod
    def create(cls, int_phone_number, waiting_time=30):
        key = generate_code(cls)
        code = cls._default_manager.create(
            phone_number=int_phone_number, waiting_time=waiting_time, key=key
        )
        return code

    def get_remaining_time(self):
        time_threshold = self.sent.timestamp() + self.waiting_time
        dt_now = datetime.datetime.now(timezone.utc)

        remaining_time = time_threshold - dt_now.timestamp()

        return remaining_time

    def can_create_next_code(self):
        rt = self.get_remaining_time()

        return rt <= 0

    def verify(self):
        self.verified = True
        self.save()

    def send_key(self):
        body = MessageClient._BODY_VIRIFICATION.format(self.key)

        MessageClient.send_message(body, self.phone_number)

        self.sent = datetime.datetime.now(timezone.utc)

        self.save()
