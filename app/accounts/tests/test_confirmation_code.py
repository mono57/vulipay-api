from django.test import TestCase
from accounts.models import PhoneNumberConfirmationCode


class TestPhoneNumberConfirmationCode(TestCase):
    def test_generate_unique_key(self):
        pass