from django.contrib.auth import get_user_model
from django.test import TestCase

from app.accounts.api.serializers import UserFullNameUpdateSerializer

User = get_user_model()


class UserFullNameUpdateSerializerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="test_serializer@example.com",
            password="testpassword123",
            full_name="Original Name",
        )

        self.serializer_data = {"full_name": "Updated Full Name"}

        self.serializer = UserFullNameUpdateSerializer(
            instance=self.user, data=self.serializer_data
        )

    def test_serializer_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_empty_full_name(self):
        """Test that the serializer rejects empty full_name"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_whitespace_full_name(self):
        """Test that the serializer rejects full_name with only whitespace"""
        serializer = UserFullNameUpdateSerializer(
            instance=self.user, data={"full_name": "   "}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("full_name", serializer.errors)

    def test_serializer_update_user(self):
        self.serializer.is_valid()
        self.serializer.save()

        updated_user = User.objects.get(pk=self.user.pk)
        self.assertEqual(updated_user.full_name, self.serializer_data["full_name"])

    def test_serializer_output(self):
        """Test that the serializer output contains the correct fields"""
        serializer = UserFullNameUpdateSerializer(instance=self.user)
        data = serializer.data

        self.assertIn("full_name", data)
        self.assertEqual(data["full_name"], self.user.full_name)
