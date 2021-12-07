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

    def unexpired_keys(self):
        return self.exclude(self.expired_keys())

    def expired_q(self):
        sent_threshold = timezone.now() - datetime.timedelta(
            days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
        )
        return Q(sent__lt=sent_threshold)


class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        try:
            obj = self.get(iso_code=iso_code)
            return obj.code
        except Model.DoesNotExist:
            return None