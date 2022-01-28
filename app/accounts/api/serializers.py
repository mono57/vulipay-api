from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from rest_framework import serializers

from accounts.models import AvailableCountry

import re

User = get_user_model()

class RegisterSerializer(serializers.Serializer):
    country_iso_code = serializers.CharField()
    phone_number = serializers.CharField()

    def clean_phone_number(self, phone_number):
        # First level validation: International phone number validation
        return phone_number

    def validate_country_iso_code(self, iso_code):
        if len(iso_code) != 2:
            raise serializers.ValidationError(_(f'Invalid ISO CODE {iso_code}'))
        return iso_code

    def validate(self, data):
        iso_code = data.get("country_iso_code", "")
        qs_country = AvailableCountry.objects.filter(iso_code=iso_code)

        if not qs_country.exists():
            raise serializers.ValidationError(
                _(f"Country not found with this iso code {iso_code}"))

        country: AvailableCountry = qs_country.first()
        phone_number = data.get("phone_number", "")

        if not re.match(country.phone_number_regex, phone_number):
            raise serializers.ValidationError(
                _(f'Invalid phone number {phone_number}'))

        int_phone_number = "{0}{1}{2}".format(
            settings.DIAL_OUT_CODE,
            country.calling_code,
            phone_number
        )

        data['phone_number'] = int_phone_number

        return data


class ConfirmCodeSerializer(RegisterSerializer):
    code = serializers.CharField()

    def validate_code(self, code: str):
        if not code.isdigit() and not len(code) == settings.CONFIRMATION_CODE_LENGTH:
            raise serializers.ValidationError(_('Invalid code'))
        return code