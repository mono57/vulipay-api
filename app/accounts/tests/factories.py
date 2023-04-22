from factory.django import DjangoModelFactory
from factory import Faker as faker
from app.accounts.models import *


class UserFactory(DjangoModelFactory):
    class Meta:
        model = Account

    first_name = faker('first_name')
    last_name = faker('last_name')
    email = faker('email')

class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = faker('country')
    dial_code = "237"
    iso_code = "CM"
    phone_number_regex = "ZRESDF"


class PassCodeFactory(DjangoModelFactory):
    class Meta:
        model = PassCode
