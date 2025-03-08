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


class PhoneNumberManager(models.Manager):
    def phone_number_exists(self, account, phone_number):
        qs = self.filter(Q(account=account) & Q(number=phone_number))
        if qs.exists:
            return qs.first()
        return None

    def get_verify_phonenumbers(self, account):
        qs = self.filter(Q(account=account))
        return qs
