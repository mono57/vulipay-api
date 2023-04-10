import datetime

from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager, Q
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

    def get_last_created_code(self, phone_number, country_iso_code):
        code = (
            self.filter(Q(phone_number=phone_number) & Q(country_iso_code=country_iso_code))
            .last()
        )

        return code

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

    # improve performance
    def get_user(self, phone_number, country_iso_code):
        qs = self.filter(Q(number=phone_number) & Q(country__iso_code=country_iso_code))

        if qs.exists():
            return qs.first().user

        return None