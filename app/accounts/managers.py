import datetime

from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager, Q
from django.utils import timezone


class UserManager(BaseUserManager):
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


class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        qs = self.filter(iso_code=iso_code).values("code")

        if qs.exists():
            return qs.first().get("code")

        return None


class PassCodeManager(Manager):
    def expired_keys(self):
        return self.filter(self.expired_q())

    def get_last_created_code(self, phone_number, country_iso_code):
        code = (
            self.filter(Q(phone_number=phone_number) & Q(country_iso_code=country_iso_code))
            .last()
        )

        return code

    def unexpired_keys(self):
        return self.exclude(self.expired_keys())

    def expired_q(self):
        sent_threshold = timezone.now() - datetime.timedelta(
            days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
        )
        return Q(sent_date__lt=sent_threshold)

    def to_seconds_datetime(_datetime):
        return _datetime.timestamp()