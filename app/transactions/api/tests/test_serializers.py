from django.test import TestCase

from app.transactions.api.serializers import P2PTransactionSerializer

class P2PTransactionSerializerTestCase(TestCase):
    def setUp(self) -> None:
        self.serializer = P2PTransactionSerializer

    def test_it_should_not_validate_for_wrong_amount(self):
        data = {'amount': 0}
        serializer = self.serializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

        data['amount'] = -200

        serializer = self.serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_it_should_not_validate_if_body_empty(self):
        serializer = self.serializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_it_should_validate_serializer(self):
        data = {'amount': 30}
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())
