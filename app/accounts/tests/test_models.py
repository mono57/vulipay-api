import hashlib

from django.test import TestCase

from app.accounts.models import User


class UserModelTestCase(TestCase):
    def test_phone_number_hashing(self):
        test_phone = "+1234567890"
        user = User.objects.create(
            phone_number=test_phone,
            email="test_hash@example.com",
        )

        self.assertIsNotNone(user.hashed_phone_number)

        self.assertIsInstance(user.hashed_phone_number, str)
        self.assertEqual(
            len(user.hashed_phone_number), 64
        )  # SHA-256 hexdigest is 64 chars

        # Store the original hash
        original_hash = user.hashed_phone_number

        new_phone = "+0987654321"
        user.phone_number = new_phone
        user.save()

        user.refresh_from_db()

        self.assertIsNotNone(user.hashed_phone_number)
        self.assertNotEqual(user.hashed_phone_number, original_hash)
