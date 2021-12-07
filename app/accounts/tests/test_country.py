from django.test import TestCase
from django.db import IntegrityError

from accounts.models import AvailableCountry

class TextCountry(TestCase):
    def setUp(self):
        self.payload = {
            'name': 'Tchad',
            'calling_code': '235',
            'iso_code': 'TD',
            'phone_number_regex': ""
        }

    def test_create_country_successful(self):
        country = AvailableCountry.objects.create(**self.payload)

        self.assertTrue(isinstance(country, AvailableCountry))

    def test_cant_create_two_same_country(self):
        AvailableCountry.objects.create(**self.payload)

        with self.assertRaises(IntegrityError):
            AvailableCountry.objects.create(**self.payload)