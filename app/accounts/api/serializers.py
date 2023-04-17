import math
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumbers import NumberParseException

from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber as PhoneNumberWrapper
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status

from app.accounts.crypto import PassCodeGenerator
from app.accounts.models import AvailableCountry, PhoneNumber, PassCode, User as UserModel

User: UserModel = get_user_model()
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
            raise serializers.ValidationError({**self.default_error_messages}, 'invalid_phone_number')

        if not wrapper.is_valid():
            raise serializers.ValidationError({**self.default_error_messages}, 'invalid_phone_number')

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

class VerifyPassCodeSerializer(PassCodeSerializer):
    code = serializers.CharField()

    def validate_code(self, code: str):
        passcode_wrapper = PassCodeGenerator.from_code(code)

        if not passcode_wrapper.is_valid():
            raise serializers.ValidationError(_('Invalid Code'), 'invalid_code')

        return code

    def validate(self, data):
        data = super().validate(data)

        phone_number = data.get("phone_number")
        country_iso_code = data.get("country_iso_code")

        passcode: PassCode = PassCode.objects.get_last_code(phone_number, country_iso_code)

        if passcode is None:
            raise serializers.ValidationError({'code': _("The code has not found")}, 'code_not_found')

        can_verify = passcode.check_can_verify()

        if not can_verify:
            raise serializers.ValidationError(
                f'Cannot verify the OTP. Please try again in {math.floor(passcode.next_attempt_on)} seconds.',
                'unprocessable_verification')

        if passcode.key_expired:
            raise serializers.ValidationError({'code': _("The code has been expired")}, 'code_expired')

        code = data.get("code")

        verified = passcode.verify(code)

        if not verified:
            raise serializers.ValidationError({'code': _("The code you provided is invalid")}, 'invalid_code')

        return data

    def create(self, validated_data):
        phone_number = PhoneNumber.objects.get_or_none(**validated_data)

        if phone_number is not None:
            return phone_number

        phone_number: PhoneNumber = PhoneNumber.create(
            phone_number=validated_data.get('phone_number'),
            country_iso_code=validated_data.get('country_iso_code'),
            verified=True)

        return phone_number

    def to_representation(self, instance: PhoneNumber):
        if getattr(self.errors, 'status_code', None) == status.HTTP_400_BAD_REQUEST and 'unprocessable_verification' in self.errors:
            self.errors['invalid'].status_code = 422
            return super().to_representation(instance)

        user = instance.user
        refresh = RefreshToken.for_user(user)

        repr = {"refresh": str(refresh), "access": str(refresh.access_token)}

        return repr
