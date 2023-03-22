from django.test import TestCase

from app.accounts.api.serializers import PassCodeSerializer
from app.accounts.models import AvailableCountry

class TestAccountSerializer(TestCase):
    payload = {
        "name": "Cameroun",
        "dial_code": "237",
        "iso_code": "CM",
        "phone_number_regex": "",
    }

    def setUp(self):
        self.serializer = PassCodeSerializer
        AvailableCountry.objects.create(**self.payload)

    def test_it_should_not_validate_if_any_field_missing(self):
        data = {}
        s = self.serializer(data=data)

        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)
        self.assertIn("country_iso_code", s.errors)

    def test_it_should_not_validate_if_country_not_found(self):
        data = {
            "phone_number": 60493823,
            "country_iso_code": 2323
        }

        s = self.serializer(data=data)

        self.assertFalse(s.is_valid())
        self.assertIn("country_iso_code", s.errors)

    def test_it_should_not_validate_if_phone_number_is_invalid(self):
        data = {
            "phone_number": 00000000,
            "country_iso_code": "CM"
        }

        s = self.serializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("phone_number", s.errors)


    def test_should_serialize_without_error(self):
        data = {
            "phone_number": 698049742,
            "country_iso_code": "CM"
        }

        s = self.serializer(data=data)
        assert s.is_valid() == True
