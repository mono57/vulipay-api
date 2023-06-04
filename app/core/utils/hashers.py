import datetime
import hashlib

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.crypto import get_random_string


def make_otp(sequences="0123456789"):
    otp = get_random_string(settings.OTP_LENGTH, sequences)
    return otp


def is_valid_otp(otp):
    if otp is None:
        return False

    is_valid = bool(otp.isdigit() and len(otp) == settings.OTP_LENGTH)
    return is_valid


def make_transaction_ref(type):
    import math

    allowed_consonants, allowed_vowels, allowed_digits = (
        "BCDFGHJKLMNPQRSTVWXZ",
        "AEIOUY",
        "0123456789",
    )

    salt = (
        get_random_string(1, allowed_consonants)
        + get_random_string(1, allowed_vowels)
        + get_random_string(4, allowed_digits)
    )

    timestamp = datetime.datetime.timestamp(timezone.now())
    ref = f"{type}.{salt}.{math.floor(timestamp)}"

    return ref


def make_payment_code(payment_code, type):
    hasher = SHA256PaymentCodeHasher()
    return hasher.encode(payment_code, type)


def make_pin(str_pin):
    hasher = "bcrypt_sha256"
    return make_password(str_pin, hasher)


def is_valid_payment_code(payment_code, allowed_types):
    hasher = SHA256PaymentCodeHasher()

    try:
        decoded = hasher.decode(payment_code)

        return bool(
            decoded.get("preffix") == settings.PAYMENT_CODE_PREFFIX
            and decoded.get("type") in allowed_types
        )

    except ValueError:
        return False


class SHA256PaymentCodeHasher:
    def encode(self, payment_code, type):
        hash_object = hashlib.sha256()
        hash_object.update(payment_code.encode("utf-8"))

        hash = hash_object.hexdigest()

        return "%s$%s$%s" % (settings.PAYMENT_CODE_PREFFIX, type, hash.upper())

    def decode(self, encoded):
        preffix, payment_type, hash = encoded.split("$", 2)

        return {
            "preffix": preffix,
            "hash": hash,
            "type": payment_type,
        }

    def verify(self, payment_code, encoded):
        decoded = self.decode(encoded)
        encoded_2 = self.encode(payment_code, decoded["type"])

        return encoded == encoded_2
