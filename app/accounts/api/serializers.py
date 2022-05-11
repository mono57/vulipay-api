import re

from accounts.models import AvailableCountry
from accounts.models import PhoneNumberConfirmationCode as Code
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    country_iso_code = serializers.CharField()
    phone_number = serializers.CharField()
    int_phone_number = serializers.CharField(required=False)

    def clean_phone_number(self, phone_number):
        # First level validation: International phone number validation
        return phone_number

    def validate_country_iso_code(self, iso_code):
        if len(iso_code) != 2:
            raise serializers.ValidationError(_(f"Invalid ISO CODE {iso_code}"))
        return iso_code

    def validate(self, data):
        iso_code = data.get("country_iso_code", "")
        qs_country = AvailableCountry.objects.filter(iso_code=iso_code)

        if not qs_country.exists():
            raise serializers.ValidationError(
                _(f"Country not found with this iso code {iso_code}")
            )

        country: AvailableCountry = qs_country.first()
        phone_number = data.get("phone_number", "")

        if not re.match(country.phone_number_regex, phone_number):
            raise serializers.ValidationError(_(f"Invalid phone number {phone_number}"))

        int_phone_number = "{0}{1}{2}".format(
            settings.DIAL_OUT_CODE, country.calling_code, phone_number
        )

        data["int_phone_number"] = int_phone_number

        return data


class ConfirmCodeSerializer(RegisterSerializer):
    code = serializers.CharField()

    def validate_code(self, code: str):
        if not code.isdigit() and not len(code) == settings.CONFIRMATION_CODE_LENGTH:
            raise serializers.ValidationError(_("Invalid code"))

        return code

    def validate(self, data):
        data = super().validate(data)

        int_phone_number = data.get("int_phone_number")
        code = data.get("code")

        code_obj: Code = Code.objects.filter(
            Q(phone_number=int_phone_number) & Q(key=code)
        ).last()

        if code_obj is None:
            raise serializers.ValidationError(_(f"Code not found: {code}"))

        if code_obj.key_expired:
            raise serializers.ValidationError(_(f"Code: {code} has expired"))

        code_obj.verify()

        return data
