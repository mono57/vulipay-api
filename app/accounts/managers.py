import datetime, random

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager, Q, F
from django.db.models.functions import Cast
from django.db import models
from django.utils import timezone


class AccountManager(Manager):
    @classmethod
    def generate_account_number(cls):
        return str(random.randint(0, 65535))

class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        qs = self.filter(iso_code=iso_code).values("code")

        if qs.exists():
            return qs.first().get("code")

        return None


class PassCodeManager(Manager):
    # def expired_keys(self):
    #     return self.filter(self.expired_q())

    def get_last_code(self, phone_number, country_iso_code):
        code = (
            self.filter(Q(phone_number=phone_number) & Q(country_iso_code=country_iso_code))
            .last()
        )

        return code

    def check_can_verify(self, phone_number, country_iso_code):
        dt_now = timezone.now()
        qs = super().get_queryset()
        qs_processable_passcode = qs.filter(next_attempt_on__lte=dt_now);
        print('qs.first exits', qs_processable_passcode.exists())
        # qs = self.filter(
        #     Q(country_iso_code=country_iso_code) &
        #     Q(phone_number=phone_number) &
        #     Q(verified=False) &
        #     Q(expired=False) &
        #     Q(next_attempt_on__gte=dt_now))
        passcode = qs_processable_passcode.last()
        print('dt.datetime.now(timezone.utc)', dt_now)
        print('manager next_attempt_on',passcode.next_attempt_on)
        print(qs_processable_passcode.query)
        print('super().get_queryset().last().next_attempt_on', super().get_queryset().last().next_attempt_on)
        return qs.exists(), qs.last()

    # def unexpired_keys(self):
    #     return self.exclude(self.expired_keys())

    # def expired_q(self):
    #     sent_threshold = timezone.now() - datetime.timedelta(
    #         days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
    #     )
    #     return Q(sent_date__lt=sent_threshold)

class PhoneNumberManager(Manager):
    def get_primary(self, account):
        try:
            return self.get(account=account, primary=True)
        except self.model.DoesNotExist:
            return None

    def get_or_none(self, **kwargs):
        qs = self.filter(**kwargs)

        if qs.exists():
            return qs.first()

        return None

    # improve performance
    def get_account(self, phone_number, country_iso_code):
        qs = self.filter(Q(number=phone_number) & Q(country__iso_code=country_iso_code))

        if qs.exists():
            return qs.first().account

        return None