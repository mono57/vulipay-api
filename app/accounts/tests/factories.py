from factory.django import DjangoModelFactory

from accounts.models import AvailableCountry

class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = 'Cameroun'
    calling_code = '237'
    iso_code = 'CM'
    country_code_regex = ''
