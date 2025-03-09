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

    def test_authenticate_with_email_for_email_only_user(self):
        """Test authenticating with email for a user with only email"""
        user = self.backend.authenticate(
            request=None, username="email_only@example.com", password=self.password
        )
        self.assertEqual(user, self.user_with_email)

    def test_authenticate_with_phone_for_phone_only_user(self):
        """Test authenticating with phone for a user with only phone"""
        user = self.backend.authenticate(
            request=None, username="+237698049706", password=self.password
        )
        self.assertEqual(user, self.user_with_phone)

    def test_authenticate_with_email_for_both_user(self):
        """Test authenticating with email for a user with both email and phone"""
        user = self.backend.authenticate(
            request=None, username="both@example.com", password=self.password
        )
        self.assertEqual(user, self.user_with_both)

    def test_authenticate_with_phone_for_both_user(self):
        """Test authenticating with phone for a user with both email and phone"""
        user = self.backend.authenticate(
            request=None, username="+237698049705", password=self.password
        )
        self.assertEqual(user, self.user_with_both)

    def test_authenticate_with_wrong_password(self):
        """Test authentication fails with wrong password"""
        user = self.backend.authenticate(
            request=None, username="both@example.com", password="wrongpassword"
        )
        self.assertIsNone(user)

    def test_authenticate_with_nonexistent_user(self):
        """Test authentication fails with nonexistent user"""
        user = self.backend.authenticate(
            request=None, username="nonexistent@example.com", password=self.password
        )
        self.assertIsNone(user)
