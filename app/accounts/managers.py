import datetime
import random

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
    def get_last_code(self, phone_number, country_iso_code):
        code = self.filter(Q(phone_number=phone_number) & Q(country_iso_code=country_iso_code)).last()
        return code

    def not_expired_q(self, phone_number, country_iso_code):
        return Q(country_iso_code=country_iso_code) & Q(phone_number=phone_number) & Q(expired=False)

    def can_create_passcode(self, phone_number, country_iso_code):
        qs = self.filter(self.not_expired_q(phone_number, country_iso_code)
                         & Q(next_passcode_on__gte=timezone.now())).values('next_passcode_on')

        qs_exits = qs.exists()
        next_passcode_on = qs.first().get('next_passcode_on') if qs_exits else None

        return not qs_exits, next_passcode_on

    def can_verify(self, phone_number, country_iso_code):
        qs = self.filter(self.not_expired_q(phone_number, country_iso_code)
                         & Q(next_verif_attempt_on__gte=timezone.now())).values('next_verif_attempt_on')

        qs_exits = qs.exists()
        next_verif_attempt_on = qs.first().get('next_verif_attempt_on') if qs_exits else None

        return not qs_exits, next_verif_attempt_on

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
