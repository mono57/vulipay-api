import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.accounts.managers import UserManager
from app.core.utils import AppCharField, AppModel, check_pin, make_pin


def compute_next_attempt_time(count) -> datetime.datetime:
    dt_now = timezone.now()
    time_diff = dt_now + datetime.timedelta(seconds=30 * count)

    return time_diff


def compute_next_verif_attempt_time(count) -> datetime.datetime:
    dt_now = timezone.now()
    time_diff = dt_now + datetime.timedelta(minutes=10)

    return time_diff


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
    pin = AppCharField(_("PIN"), max_length=128, null=True, blank=True)

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

    def set_pin(self, pin):
        self.pin = make_pin(pin)
        self.save()

    def verify_pin(self, raw_pin):
        is_correct = check_pin(self.pin, raw_pin)
        return is_correct


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
    country = models.ForeignKey(
        AvailableCountry,
        null=True,
        on_delete=models.SET_NULL,
        related_name="currencies",
    )

    def __str__(self):
        return f"{self.name} - {self.iso_code} - {self.symbol}"
