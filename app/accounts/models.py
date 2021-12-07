from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

from app.utils.timestamp import TimestampModel
from app.utils.generate_code import generate_code
from accounts.managers import (
    PhoneNumberConfirmationCodeManager,
    AvailableCountryManager,
    UserManager)

import datetime


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('Email address'), unique=True)
    phone_number = models.CharField(_("Phone number"), max_length=20)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class AvailableCountry(TimestampModel):
    name = models.CharField(max_length=30) # i.e Chad
    calling_code = models.CharField(max_length=5, unique=True) # i.e 235
    iso_code = models.CharField(max_length=10, unique=True) # i.e TD
    phone_number_regex = models.CharField(max_length=50)

    objects = AvailableCountryManager()

    def __str__(self):
        return f'({self.calling_code}) - {self.name} - {self.iso_code}'

class NetworkProvider(TimestampModel):
    name = models.CharField(max_length=30, verbose_name=_('name'))

    def __str__(self):
        return self.name

class PhoneNumber(TimestampModel):
    number = models.CharField(max_length=20)
    primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    provider = models.ForeignKey(NetworkProvider, blank=True, null=True, on_delete=models.SET_NULL)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='phone_numbers',
        verbose_name=_('User')
    )
    country = models.ForeignKey(
        AvailableCountry,
        on_delete=models.CASCADE,
        related_name='phone_numbers'
    )

    def __str__(self):
        return f'({self.country.calling_code}) {self.number}'


class PhoneNumberConfirmationCode(TimestampModel):
    phone_number = models.CharField(max_length=20)
    key = models.CharField(max_length=8)
    sent = models.DateTimeField(null=True)

    objects = PhoneNumberConfirmationCodeManager()

    def __str__(self):
        return self.key

    def key_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            days=settings.CODE_EXPIRE_DAYS
            )

        return expiration_date <= timezone.now()

    @classmethod
    def create(cls, phone_number):
        key = generate_code(__class__)
        return cls._default_manager.create(phone_number=phone_number, key = key)

    def send_key(self):
        # Send confirmation code here
        print("Code sent", self.key)
