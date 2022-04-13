import datetime

from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.db.models import Manager, Q
from django.db.models.base import Model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, phone_number, **kwargs):
        if not phone_number:
            raise ValueError(_("Phone number must be set"))

        user = self.model(phone_number=phone_number, **kwargs)

        user.save()

        return user

    def create_superuser(self, email, password, **kwargs):
        if not email:
            raise ValueError(_("Email must be set"))

        user = self.model(email=self.normalize_email(email), **kwargs)
        user.set_password(password)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True

        user.save()

        return user


class PhoneNumberConfirmationCodeManager(Manager):
    def expired_keys(self):
        return self.filter(self.expired_q())

    def get_last_created_code(self, int_phone_number):
        code = (
            self.filter(phone_number=int_phone_number).order_by("-created_at").first()
        )

        return code

    def unexpired_keys(self):
        return self.exclude(self.expired_keys())

    def expired_q(self):
        sent_threshold = timezone.now() - datetime.timedelta(
            days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
        )
        return Q(sent__lt=sent_threshold)

    def to_seconds_datetime(_datetime):
        return _datetime.timestamp()


class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        try:
            obj = self.get(iso_code=iso_code)
            return obj.code
        except Model.DoesNotExist:
            return None
