from accounts.models import AvailableCountry, PhoneNumberConfirmationCode
from factory.django import DjangoModelFactory


class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = "Cameroun"
    calling_code = "237"
    iso_code = "CM"
    country_code_regex = ""


class CodeFactory(DjangoModelFactory):
    class Meta:
        model = PhoneNumberConfirmationCode
