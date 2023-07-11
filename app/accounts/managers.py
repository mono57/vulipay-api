import datetime
import random

from django.conf import settings
from django.db import models
from django.db.models import F, Manager, Q
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AccountManager(Manager):
    @classmethod
    def generate_account_number(cls):
        # Note: DEV only
        return str(random.randint(0, 65535))

    def create_master_account(self):
        self.create(
            intl_phone_number=settings.MASTER_INTL_PHONE_NUMBER,
            phone_number=settings.MASTER_PHONE_NUMBER,
            is_master=True,
        )

    def credit_master_account(self, amount):
        self.filter(
            Q(is_master=True) & Q(intl_phone_number=settings.MASTER_INTL_PHONE_NUMBER)
        ).update(balance=F("balance") + amount)


class PassCodeManager(Manager):
    def get_last_code(self, intl_phone_number):
        code = self.filter(Q(intl_phone_number=intl_phone_number)).last()
        return code

    def not_expired_q(self, intl_phone_number):
        return Q(intl_phone_number=intl_phone_number) & Q(expired=False)

    def can_create_passcode(self, intl_phone_number):
        qs = self.filter(
            self.not_expired_q(intl_phone_number)
            & Q(next_passcode_on__gte=timezone.now())
        ).values("next_passcode_on")

        qs_exits = qs.exists()
        next_passcode_on = qs.first().get("next_passcode_on") if qs_exits else None

        return not qs_exits, next_passcode_on

    def can_verify(self, intl_phone_number):
        qs = self.filter(
            self.not_expired_q(intl_phone_number)
            & Q(next_verif_attempt_on__gte=timezone.now())
        ).values("next_verif_attempt_on")

        qs_exits = qs.exists()
        next_verif_attempt_on = (
            qs.first().get("next_verif_attempt_on") if qs_exits else None
        )

        return not qs_exits, next_verif_attempt_on
