import datetime

from countries.models import AvailableCountry, NetworkProvider
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from otp_auth.managers import PassCodeManager
from utils.generate_code import generate_code
from utils.models import AppModel
from utils.twilio_client import MessageClient

User = settings.AUTH_USER_MODEL


class PhoneNumber(AppModel):
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


class PassCode(AppModel):
    phone_number = models.CharField(max_length=20)
    key = models.CharField(max_length=8)
    sent = models.DateTimeField(null=True)
    verified = models.BooleanField(default=False)
    waiting_time = models.IntegerField(default=30)  # waiting time to send new code

    objects = PassCodeManager()

    def __str__(self):
        return self.key

    @property
    def key_expired(self):
        if self.verified:
            return True

        expiration_date = self.sent + datetime.timedelta(
            days=settings.CODE_EXPIRATION_DAYS
        )

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
