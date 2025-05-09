from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.test import TestCase

from app.accounts.models import User
from app.accounts.tests.factories import AvailableCountryFactory, UserFactory


class UserManagerTestCase(TestCase):
    def setUp(self):
        self.country = AvailableCountryFactory.create()

    def test_create_user_with_email(self):
        """Test creating a user with email only"""
        user = User.objects.create_user(
            email="email_only@example.com", password="testpass123"
        )
        self.assertEqual(user.email, "email_only@example.com")
        self.assertIsNone(user.phone_number)
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_with_phone(self):
        """Test creating a user with phone number only"""
        user = User.objects.create_user(
            phone_number="+237698049702", password="testpass123"
        )
        self.assertEqual(user.phone_number, "+237698049702")
        self.assertIsNone(user.email)
        self.assertTrue(user.check_password("testpass123"))

    def test_create_user_with_both(self):
        """Test creating a user with both email and phone number"""
        user = User.objects.create_user(
            email="both@example.com",
            phone_number="+237698049703",
            password="testpass123",
        )
        self.assertEqual(user.email, "both@example.com")
        self.assertEqual(user.phone_number, "+237698049703")

    def test_create_user_without_password(self):
        """Test creating a user without a password"""
        user = User.objects.create_user(email="nopass@example.com")
        self.assertFalse(user.has_usable_password())

    def test_create_user_normalize_email(self):
        """Test email is normalized when creating a user"""
        email = "test@EXAMPLE.COM"
        user = User.objects.create_user(email=email)
        self.assertEqual(user.email, email.lower())

    def test_create_user_invalid_email(self):
        """Test creating user with no email or phone raises error"""
        with self.assertRaises(ValidationError):
            User.objects.create_user(email=None, phone_number=None)

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email="super@example.com", password="testpass123"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_without_email(self):
        """Test creating a superuser without email raises error"""
        with self.assertRaises(ValidationError):
            User.objects.create_superuser(email=None, password="testpass123")

    def test_create_superuser_without_password(self):
        """Test creating a superuser without password raises error"""
        with self.assertRaises(ValidationError):
            User.objects.create_superuser(email="super@example.com", password=None)

    def test_superuser_staff_flag_honored(self):
        """Test that is_staff=False is honored when creating a superuser"""
        user = User.objects.create_superuser(
            email="super@example.com", password="testpass123", is_staff=False
        )
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_superuser_flag_honored(self):
        """Test that is_superuser=False is honored when creating a superuser"""
        user = User.objects.create_superuser(
            email="super@example.com", password="testpass123", is_superuser=False
        )
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_get_by_natural_key_email(self):
        """Test retrieving a user by email using get_by_natural_key"""
        user = UserFactory.create(email="natural@example.com")
        retrieved_user = User.objects.get_by_natural_key("natural@example.com")
        self.assertEqual(user, retrieved_user)

    def test_get_by_natural_key_phone(self):
        """Test retrieving a user by phone number using get_by_natural_key"""
        user = UserFactory.create(phone_number="+237698049704")
        retrieved_user = User.objects.get_by_natural_key("+237698049704")
        self.assertEqual(user, retrieved_user)
