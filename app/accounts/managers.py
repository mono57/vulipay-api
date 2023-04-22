import datetime, random

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager, Q
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
    def get_primary(self, account):
        try:
            return self.get(account=account, primary=True)
        except self.model.DoesNotExist:
            return None

    # improve performance
    def get_account(self, phone_number, country_iso_code):
        qs = self.filter(Q(number=phone_number) & Q(country__iso_code=country_iso_code))

        if qs.exists():
            return qs.first().account

        return None