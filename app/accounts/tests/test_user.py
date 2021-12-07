from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestUser(TestCase):
    def test_create_user_successful(self):
        phone_number = '698049742'

        user = User.objects.create_user(phone_number)

        self.assertEqual(user.phone_number, phone_number)

    def test_create_user_fail(self):
        phone_number = ''

        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number)
