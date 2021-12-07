from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import AvailableCountry
from accounts.tests.factories import AvailableCountryFactory

User = get_user_model()

CREATE_USER_URL = reverse('accounts:register')
CONFIRM_CODE_URL = reverse('accounts:confirm')

class TestPublicUserApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.country_payload = {
            'name': 'Cameroun',
            'calling_code': '237',
            'phone_number_regex': '^6[5-9][0-9]{7}$',
            'iso_code': 'CM'
        }
        AvailableCountry.objects.create(**self.country_payload)

    def test_country_available(self):
        country = AvailableCountry.objects.get(**self.country_payload)

        self.assertTrue(isinstance(country, AvailableCountry))


    def test_create_inactive_user(self):
        payload = {
            'phone_number': '698049742',
            'country_iso_code': 'CM'
        }
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertTrue(response.status_code == status.HTTP_201_CREATED)


    def test_can_confirm_code(self):
        pass