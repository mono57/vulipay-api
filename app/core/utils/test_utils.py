from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import serializers

from app.core.utils import AppAmountField, hashers
from app.core.utils.network_carrier import NO_CARRIER, get_carrier


class TestGetCarrier(SimpleTestCase):
    def setUp(self):
        self.phone_number = "698049334"
        self.country_iso_code = "CM"

    def test_should_return_str_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertTrue(isinstance(carrier, str))

    def test_it_should_return_correct_carrier_name(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertIn("orange", carrier.lower())

    def test_it_should_return_unknow_if_not_identify(self):
        carrier = get_carrier("60344544", self.country_iso_code)

        self.assertEqual(carrier, NO_CARRIER)

    def test_it_should_have_country_code_as_prefix(self):
        carrier = get_carrier(self.phone_number, self.country_iso_code)

        self.assertEqual(self.country_iso_code, carrier[:2])


class SHA256PaymentCodeHasherTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.hasher = hashers.SHA256PaymentCodeHasher()

    def test_it_encode(self):
        code = "YTREZFGHJH456765"
        encoded = self.hasher.encode(code, "CST")
        # vulipay$CST$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0
        self.assertNotEqual(code, encoded)

        preffix, type, hash = encoded.split("$")

        self.assertEqual(settings.PAYMENT_CODE_PREFFIX, preffix)
        self.assertEqual(type, "CST")
        self.assertNotEqual(code, hash)

    def test_it_decode(self):
        encoded = "vulipay$CST$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0"
        decoded = self.hasher.decode(encoded)

        self.assertIn("preffix", decoded)
        self.assertIn("type", decoded)
        self.assertIn("hash", decoded)


class MakeTransactionRefTestCase(SimpleTestCase):
    def test_it_make_transaction_ref(self):
        ref = hashers.make_transaction_ref("P2P")
        type, salt, _ = ref.split(".")

        self.assertEqual(type, "P2P")
        self.assertEqual(len(salt), 6)
        self.assertTrue(salt[:2].isalpha())
        self.assertTrue(salt[2:].isdigit())


class IsValidPaymentCodeTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.fake_transaction_types = ("PPE", "FRE")

    def test_it_should_validate_payment_code(self):
        self.assertTrue(
            hashers.is_valid_payment_code(
                "vulipay$PPE$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )
        self.assertTrue(
            hashers.is_valid_payment_code(
                "vulipay$FRE$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )

    def test_it_should_not_validate_payment_code(self):
        self.assertFalse(
            hashers.is_valid_payment_code(
                "vulipay$PEF$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )
        self.assertFalse(
            hashers.is_valid_payment_code(
                "vulipay$PPE$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                (),
            )
        )
        self.assertFalse(
            hashers.is_valid_payment_code(
                "$PE$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )
        self.assertFalse(
            hashers.is_valid_payment_code(
                "vulipay$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )
        self.assertFalse(
            hashers.is_valid_payment_code(
                "vulipay$$64DF7B1D1445B49799B280E395E3E065D369808F2D924E411EEE9C23293D05B0",
                self.fake_transaction_types,
            )
        )


class OTPTestCase(SimpleTestCase):
    def test_it_make_otp(self):
        otp = hashers.make_otp()

        self.assertEqual(len(otp), settings.OTP_LENGTH)
        self.assertTrue(otp.isdigit())

    def test_it_is_valid_otp(self):
        self.assertTrue(hashers.is_valid_otp("765434"))
        self.assertFalse(hashers.is_valid_otp("75434"))
        self.assertFalse(hashers.is_valid_otp("7E5434"))
        self.assertFalse(hashers.is_valid_otp("7653434"))
        self.assertFalse(hashers.is_valid_otp(None))


@patch("app.core.utils.hashers.make_password")
class MakePinCode(TestCase):
    def setUp(self) -> None:
        self.pin_to_hash = "1234"

    def test_it_should_hash_pin_code(self, mocked_make_password: MagicMock):
        hashers.make_pin(self.pin_to_hash)
        mocked_make_password.assert_called_once_with(self.pin_to_hash, "bcrypt_sha256")

    # @override_settings(
    #     PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
    # )
    # def test_it_should_raise_exception_when_hasher_not_found(
    #     self, mocked_make_password: MagicMock
    # ):
    #     with self.assertRaises(ValueError):
    #         settings
    #         hashers.make_pin_code(self.pin_to_hash)


@patch("app.core.utils.hashers.check_password")
class CheckPin(TestCase):
    def test_check_pin(self, mocked_check_password: MagicMock):
        pin, encoded = "2324", "GHGDDFGHGFDERTYTRE"
        hashers.check_pin(pin=pin, raw_pin=encoded)
        mocked_check_password.assert_called_once_with(
            encoded, pin, preferred="bcrypt_sha256"
        )


class AppAmountFieldTest(serializers.Serializer):
    amount = AppAmountField()


class TestAppAmountField(TestCase):
    def test_it_should_raise_min_value_error(self):
        class AppAmountFieldTest(serializers.Serializer):
            amount = AppAmountField()

        s = AppAmountFieldTest(data={"amount": -1})

        self.assertFalse(s.is_valid())
        self.assertIn("amount", s.errors)

    def test_it_should_validate_with_value_less_than_0(self):
        class AppAmountFieldTest(serializers.Serializer):
            amount = AppAmountField(min_value=-10)

        s = AppAmountFieldTest(data={"amount": -1})

        self.assertTrue(s.is_valid())
