from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumbers import NumberParseException

from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber as PhoneNumberWrapper

from app.accounts.models import AvailableCountry, PhoneNumber, PassCode

User = get_user_model()

class PassCodeSerializer(serializers.Serializer):
    country_iso_code = serializers.CharField()
    phone_number = serializers.CharField()

    default_error_messages = {
        'phone_number': _("The number you provided is not valid, please choose another one. \
                            Feel free to reach us on help.vulipay.com if the error persist")
    }

    def validate_country_iso_code(self, iso_code):
        qs_country = AvailableCountry.objects.filter(iso_code=iso_code)

        if not qs_country.exists():
            raise serializers.ValidationError(
                _("Vulipay's services are not available in your country.")
            )

        return iso_code

    def validate(self, data):
        country_iso_code = data["country_iso_code"]
        phone_number = data["phone_number"]

        try:
            wrapper = PhoneNumberWrapper.from_string(phone_number=phone_number, region=country_iso_code)
        except NumberParseException:
            raise serializers.ValidationError({ **self.default_error_messages }, 'invalid_phone_number')

        if not wrapper.is_valid():
            raise serializers.ValidationError({ **self.default_error_messages }, 'invalid_phone_number')

        return data

    def create(self, validated_data):
        code: PassCode = PassCode.create(
            validated_data['phone_number'],
            validated_data['country_iso_code'])

        return code

    def to_representation(self, instance: PassCode):
        repr = {
            **super().to_representation(instance),
            "waiting_time": instance.get_remaining_time()
        }
        return repr

# class ConfirmCodeSerializer(RegisterSerializer):
#     code = serializers.CharField()

#     def validate_code(self, code: str):
#         if not code.isdigit() and not len(code) == settings.CONFIRMATION_CODE_LENGTH:
#             raise serializers.ValidationError(_("Invalid code"))

#         return code

#     def validate(self, data):
#         data = super().validate(data)

#         int_phone_number = data.get("int_phone_number")
#         code = data.get("code")

#         code_obj: PassCode = PassCode.objects.filter(
#             Q(phone_number=int_phone_number) & Q(key=code)
#         ).last()

#         if code_obj is None:
#             raise serializers.ValidationError(_(f"Code not found: {code}"))

#         if code_obj.key_expired:
#             raise serializers.ValidationError(_(f"Code: {code} has expired"))

#         code_obj.verify()

#         return data
