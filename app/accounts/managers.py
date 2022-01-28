from typing import Union
from django.db.models import Q, Manager
from django.db.models.base import Model
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

import datetime


class UserManager(BaseUserManager):
    def create_user(self, phone_number, **kwargs):
        if not phone_number:
            raise ValueError(_('Phone number must be set'))

        user = self.model(
            phone_number=phone_number,
            **kwargs
        )

        user.save()

        return user

    def create_superuser(self, email, password, **kwargs):
        if not email:
            raise ValueError(_('Email must be set'))

        user = self.model(
            email=self.normalize_email(email),
            **kwargs
        )
        user.set_password(password)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True

        user.save()

        return user


class PhoneNumberConfirmationCodeManager(Manager):
    def expired_keys(self):
        return self.filter(self.expired_q())

    # def force_expired(self, int_phone_number):
    #     unexpired_keys = self.unexpired_keys()
    #     phone_number_unexpired_keys = unexpired_keys.filter(
    #         phone_number = int_phone_number
    #     )
    #     phone_number_unexpired_keys.update()

    def unexpired_keys(self):
        return self.exclude(self.expired_keys())

    def expired_q(self):
        sent_threshold = timezone.now() - datetime.timedelta(
            days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
        )
        return Q(sent__lt=sent_threshold)

    def to_seconds_datetime(_datetime):
        return _datetime.timestamp()

    def check_can_send_code(self, int_phone_number):
        qs = self.filter(Q(phone_number=int_phone_number) & self.expired_q)
        last_code = qs.last()

        remaining_time = 30 # seconds

        if not last_code:
            return True, remaining_time

        now_seconds = self.to_seconds_datetime(datetime.datetime.now())
        time_threshold = last_code.sent + last_code.waiting_time

        remaining_time =  time_threshold - now_seconds

        return now_seconds > time_threshold, remaining_time


class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        try:
            obj = self.get(iso_code=iso_code)
            return obj.code
        except Model.DoesNotExist:
            return None