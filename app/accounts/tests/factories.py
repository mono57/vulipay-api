from factory.django import DjangoModelFactory
from factory import Faker as faker
from accounts.models import *


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = faker('first_name')
    last_name = faker('last_name')
    email = faker('email')

class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = faker('country')
    calling_code = "237"
    iso_code = "CM"
    country_code_regex = ""


class PassCodeFactory(DjangoModelFactory):
    class Meta:
        model = PassCode
