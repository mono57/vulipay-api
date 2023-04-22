from django.test import SimpleTestCase

from accounts.crypto import Hasher

class HasherTestCase(SimpleTestCase):
    def setUp(self):
        self.hashed = Hasher.hash("23456787654323456")

    def test_it_should_hash_string(self):
        self.assertIsNotNone(self.hashed)
        self.assertIsInstance(self.hashed, str)

    def test_it_should_output_same_hash_for_same_string(self):
        hashed2 = Hasher.hash("23456787654323456")

        self.assertEqual(self.hashed, hashed2)

    def test_it_should_output_64bits_hash(self):
        self.assertEqual(len(self.hashed), 64)
