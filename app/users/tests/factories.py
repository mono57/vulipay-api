from factory.django import DjangoModelFactory

from app.countries.models import AvailableCountry
from app.otp_auth.models import PassCode


class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = "Cameroun"
    calling_code = "237"
    iso_code = "CM"
    country_code_regex = ""


class PassCodeFactory(DjangoModelFactory):
    class Meta:
        model = PassCode
