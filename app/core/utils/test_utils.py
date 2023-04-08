from django.test import TestCase, SimpleTestCase

from app.core.utils.models import TimestampModel
from app.core.utils.network_carrier import get_carrier, NO_CARRIER

class TestGetCarrier(SimpleTestCase):
    def setUp(self):
        self.phone_number = '698049334'
        self.country_iso_code = 'CM'

    def test_should_return_str_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(carrier, str))

    def test_it_should_return_correct_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertIn('orange', carrier.lower())

    def test_it_should_return_unknow_if_not_identify(self):
        carrier = get_carrier('60344544', self.country_iso_code)

        self.assertEqual(carrier, NO_CARRIER)

    def test_it_should_have_country_code_as_prefix(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertEqual(self.country_iso_code, carrier[:2])