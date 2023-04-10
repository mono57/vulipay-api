import datetime

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

from app.core.utils import MessageClient, generate_code, AppModel, AppCharField, get_carrier

from app.accounts.managers import PhoneNumberManager, UserManager, AvailableCountryManager, PassCodeManager

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

    @property
    def is_verified(self):
        return self.verified

    @classmethod
    def create(cls, phone_number, country_iso_code):
        last_code: cls = cls.objects.get_last_created_code(phone_number, country_iso_code)

        if last_code and not last_code.is_verified and not last_code.waiting_time_expired():
            return last_code

        waiting_time = settings.DEFAULT_WAITING_TIME_SECONDS

        if last_code and not last_code.is_verified and last_code.waiting_time_expired():
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

        if matched:
            self.set_verified()

        return matched

    def get_remaining_time(self):
        time_threshold = self.sent_date.timestamp() + self.waiting_time
        dt_now = datetime.datetime.now(timezone.utc)

        remaining_time = time_threshold - dt_now.timestamp()

        return remaining_time

    def waiting_time_expired(self):
        rt = self.get_remaining_time()

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


class User(AbstractBaseUser, AppModel, PermissionsMixin):
    email = models.EmailField(_("Email address"), unique=True, blank=True)
    first_name = AppCharField(_("Firstname"), max_length=50, null=True)
    last_name = AppCharField(_("Lastname"), max_length=50, null=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: UserManager = UserManager()

    def __str__(self):
        return self.email

    # @classmethod
    # def get_or_create(cls, phone_number, country_iso_code, **kwargs):
    #     user, created = cls.objects.get_or_create(phone_number=phone_number, **kwargs)

    #     if not created:
    #         return user

    #     PhoneNumber.create(
    #         phone_number=phone_number,
    #         user=user,
    #         country_iso_code=country_iso_code,
    #         verified=True)

    #     return user

class PhoneNumber(AppModel):
    number = AppCharField(max_length=20)
    primary = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    carrier = AppCharField(_("Carrier"), max_length=50)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
        verbose_name=_("User"),
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

        user = User.objects.create_user()

        carrier = get_carrier(phone_number, country_iso_code)

        obj = cls.objects.create(
            number=phone_number,
            user_id=user.id,
            country_id=country_id,
            carrier=carrier,
            verified=verified)

        return obj

    def set_primary(self):
        self.primary = True
        self.save()