import factory
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from factory import Faker as faker
from factory import django

from app.accounts.models import *


class UserFactory(django.DjangoModelFactory):
    class Meta:
        model = Account

    first_name = faker("first_name")
    last_name = faker("last_name")
    email = faker("email")


class AvailableCountryFactory(django.DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = "Cameroun"
    dial_code = "237"
    iso_code = "CM"
    phone_number_regex = "ZRESDF"


class AccountFactory(django.DjangoModelFactory):
    class Meta:
        model = Account

    phone_number = "698049742"
    intl_phone_number = "+237698049742"
    country = factory.SubFactory(AvailableCountryFactory)

    @classmethod
    def create_master_account(self, **kwargs):
        kwargs.setdefault("is_master", True)
        kwargs.setdefault("phone_number", settings.MASTER_PHONE_NUMBER)
        kwargs.setdefault("intl_phone_number", settings.MASTER_INTL_PHONE_NUMBER)
        kwargs.setdefault("balance", 0)

        return self.create(**kwargs)


class PassCodeFactory(django.DjangoModelFactory):
    class Meta:
        model = PassCode

    intl_phone_number = "+237698049742"
    code = "987657"
    sent_on = timezone.now()
    next_verif_attempt_on = timezone.now()
    next_passcode_on = timezone.now()


class CarrierFactory(django.DjangoModelFactory):
    class Meta:
        model = SupportedMobileMoneyCarrier

    name = "Orange"
    country = factory.SubFactory(AvailableCountryFactory)
    # flag = SimpleUploadedFile("face.jpg", b"file data")


class PhoneNumberFactory(django.DjangoModelFactory):
    class Meta:
        model = PhoneNumber

    number = "698049741"
    carrier = factory.SubFactory(CarrierFactory)
    account = factory.SubFactory(AccountFactory)
