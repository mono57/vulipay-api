import datetime as dt

from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager, Q, F
from django.db.models.functions import Cast
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def _create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        # user.full_clean()

        if password is not None:
            user.set_password(password)

        user.save(using=self._db)

        return user

    def create_user(self, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(**extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email must be set"))

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


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
    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except self.model.DoesNotExist:
            return None

    def get_or_none(self, **kwargs):
        qs = self.filter(**kwargs)

        if qs.exists():
            return qs.first()

        return None

    # improve performance
    def get_user(self, phone_number, country_iso_code):
        qs = self.filter(Q(number=phone_number) & Q(country__iso_code=country_iso_code))

        if qs.exists():
            return qs.first().user

        return None