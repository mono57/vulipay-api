from django.test import TestCase
from rest_framework import serializers

from app.accounts.validators import pin_validator


class PinValidatorTestCase(TestCase):
    def test_it_should_not_validate_pin(self):
        with self.assertRaises(serializers.ValidationError):
            pin_validator("0987")
            pin_validator("4321")
            pin_validator("5678")
            pin_validator("8765")
            pin_validator("2345")
            pin_validator("5432")
            pin_validator("3456")
            pin_validator("6543")
            pin_validator("4567")
            pin_validator("7654")
            pin_validator("5678")
            pin_validator("6789")
            pin_validator("7890")
            pin_validator("9876")
            pin_validator("SDFF")
            pin_validator("23IK")
            pin_validator("19342")
            pin_validator("193")

    def test_it_should_validate_pin(self):
        self.assertEqual("4241", pin_validator("4241"))
