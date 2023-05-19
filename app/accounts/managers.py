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

class PassCodeManager(Manager):
    def get_last_code(self, intl_phone_number):
        code = self.filter(Q(intl_phone_number=intl_phone_number)).last()
        return code

    def not_expired_q(self, intl_phone_number):
        return Q(intl_phone_number=intl_phone_number) & Q(expired=False)

    def can_create_passcode(self, intl_phone_number):
        qs = self.filter(self.not_expired_q(intl_phone_number)
                         & Q(next_passcode_on__gte=timezone.now())).values('next_passcode_on')

        qs_exits = qs.exists()
        next_passcode_on = qs.first().get('next_passcode_on') if qs_exits else None

        return not qs_exits, next_passcode_on

    def can_verify(self, intl_phone_number):
        qs = self.filter(self.not_expired_q(intl_phone_number)
                         & Q(next_verif_attempt_on__gte=timezone.now())).values('next_verif_attempt_on')

        qs_exits = qs.exists()
        next_verif_attempt_on = qs.first().get('next_verif_attempt_on') if qs_exits else None

        return not qs_exits, next_verif_attempt_on