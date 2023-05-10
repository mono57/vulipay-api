from unittest.mock import patch, MagicMock

from django.test import TestCase, SimpleTestCase
from django.conf import settings

from app.core.utils.models import TimestampModel
from app.core.utils.network_carrier import get_carrier, NO_CARRIER
from app.core.utils.hashers import SHA256PaymentCodeHasher, make_transaction_ref

class TestGetCarrier(SimpleTestCase):
    def setUp(self):
        self.phone_number = '698049334'
        self.country_iso_code = 'CM'

    def test_should_return_str_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(carrier, str))

    def test_it_should_return_correct_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertIn('orange', carrier.lower())

    def test_it_should_return_unknow_if_not_identify(self):
        carrier = get_carrier('60344544', self.country_iso_code)

        self.assertEqual(carrier, NO_CARRIER)

    def test_it_should_have_country_code_as_prefix(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertEqual(self.country_iso_code, carrier[:2])


class SHA256PaymentCodeHasherTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.hasher = SHA256PaymentCodeHasher()

    def test_it_encode(self):
        code = 'YTREZFGHJH456765'
        encoded = self.hasher.encode(code, 'CST')
        # vulipay$CST$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0
        self.assertNotEqual(code, encoded)

        preffix, type, hash = encoded.split('$')

        self.assertEqual(settings.PAYMENT_CODE_PREFFIX, preffix)
        self.assertEqual(type, 'CST')
        self.assertNotEqual(code, hash)

    def test_it_decode(self):
        encoded = 'vulipay$CST$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0'
        decoded = self.hasher.decode(encoded)

        self.assertIn('preffix', decoded)
        self.assertIn('type', decoded)
        self.assertIn('hash', decoded)

class MakeTransactionRefTestCase(SimpleTestCase):
    def test_it_make_transaction_ref(self):
        ref = make_transaction_ref('P2P')
        type, salt, _ = ref.split('.')

        self.assertEqual(type, 'P2P')
        self.assertEqual(len(salt), 6)
        self.assertTrue(salt[:2].isalpha())
        self.assertTrue(salt[2:].isdigit())

