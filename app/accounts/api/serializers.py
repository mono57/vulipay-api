from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from phonenumbers import NumberParseException
from phonenumber_field.phonenumber import PhoneNumber as PhoneNumberWrapper

from app.core.utils import UnprocessableEntityError
from app.accounts.crypto import PassCodeGenerator
from app.accounts.models import AvailableCountry, PhoneNumber, PassCode, Account

class AbstractPassCodeSerializer(serializers.Serializer):
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

class CreatePasscodeSerializer(AbstractPassCodeSerializer):
    def validate(self, data):
        data = super().validate(data)
        phone_number = data.get("phone_number")
        country_iso_code = data.get("country_iso_code")

        can_process, next_passcode_on = PassCode.objects.can_create_passcode(phone_number, country_iso_code)

        if not can_process:
            raise UnprocessableEntityError(
                f'You can\'t send new OTP right now because of your multiple attempts. Please try again in {next_passcode_on} seconds.',
                'unprocessable_passcode')

        return data

    def create(self, validated_data):
        code: PassCode = PassCode.create(
            validated_data['phone_number'],
            validated_data['country_iso_code'])

        return code

    def to_representation(self, instance: PassCode):
        repr = {
            **super().to_representation(instance),
            "next_passcode_on": instance.next_passcode_on
        }
        return repr

class VerifyPassCodeSerializer(AbstractPassCodeSerializer):
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

        can_process, next_verif_attempt_on = PassCode.objects.can_verify(phone_number, country_iso_code)

        if not can_process:
            raise UnprocessableEntityError(
                f'You can\'t verify our OTP right now because of your multiple attempts. Please try again in {next_verif_attempt_on} seconds.',
                'unprocessable_passcode')

        passcode: PassCode = PassCode.objects.get_last_code(phone_number, country_iso_code)

        if passcode is None:
            raise serializers.ValidationError({'code': _("The code has not found")}, 'code_not_found')

        if passcode.key_expired:
            raise serializers.ValidationError({'code': _("The code has been expired")}, 'code_expired')

        code = data.get("code")

        verified = passcode.verify(code)

        if not verified:
            raise serializers.ValidationError({'code': _("The code you provided is invalid")}, 'invalid_code')

        return data

    def create(self, validated_data):
        account = PhoneNumber.objects.get_account(
            validated_data.get('phone_number'),
            validated_data.get('country_iso_code')
        )

        if account is not None:
            return account

        phone_number: PhoneNumber = PhoneNumber.create(
            phone_number=validated_data.get('phone_number'),
            country_iso_code=validated_data.get('country_iso_code'),
            verified=True)

        account = phone_number.account

        return account

    def to_representation(self, instance: Account):
        refresh = RefreshToken.for_user(instance)

        repr = {"refresh": str(refresh), "access": str(refresh.access_token)}

        return repr

class AccountPaymentCodeSerializer(serializers.Serializer):
    payment_code = serializers.CharField()


class AccountDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('number', 'owner_first_name', 'owner_last_name')