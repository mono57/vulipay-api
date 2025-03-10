from django.contrib.auth import get_user_model
from django.test import TestCase

from app.accounts.backends import EmailOrPhoneNumberBackend
from app.accounts.tests.factories import UserFactory


class EmailOrPhoneNumberBackendTestCase(TestCase):
    def setUp(self):
        self.backend = EmailOrPhoneNumberBackend()
        self.password = "testpass123"

        # Create a user with both email and phone
        self.user_with_both = UserFactory.create_with_password(
            email="both@example.com",
            phone_number="+237698049705",
            password=self.password,
        )

        # Create a user with email only
        self.user_with_email = UserFactory.create_with_password(
            email="email_only@example.com", phone_number=None, password=self.password
        )

        # Create a user with phone only
        self.user_with_phone = UserFactory.create_with_password(
            email=None, phone_number="+237698049706", password=self.password
        )
