from django.test import TestCase

from app.utils.generate_code import generate_code
from accounts.models import PhoneNumberConfirmationCode

class TestConfirmationCode(TestCase):
    def test_should_generate_unique_code(self):
        key: str = generate_code(PhoneNumberConfirmationCode)

        self.assertTrue(isinstance(key, str))
        self.assertTrue(key.isdigit())
        self.assertTrue(len(key) == 6)