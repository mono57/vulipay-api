from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumber_field.phonenumber import PhoneNumber as PhoneNumberWrapper
from phonenumbers import NumberParseException
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import (
    Account,
    AvailableCountry,
    PassCode,
    PhoneNumber,
    SupportedMobileMoneyCarrier,
)
from app.accounts.validators import pin_validator
from app.core.utils import UnprocessableEntityError, is_valid_otp


class PINSerializerMixin:
    pin = serializers.CharField()


class AbstractPassCodeSerializer(serializers.Serializer):
    country_iso_code = serializers.CharField()
    phone_number = serializers.CharField()

    default_error_messages = {
        "phone_number": _(
            "The number you provided is not valid, please choose another one. \
                            Feel free to reach us on help.vulipay.com if the error persist"
        )
    }

    def validate_country_iso_code(self, iso_code):
        qs_country = AvailableCountry.objects.filter(iso_code=iso_code)

        if not qs_country.exists():
            raise serializers.ValidationError(
                _("Vulipay's services are not available in your country.")
            )
        self.context["country"] = qs_country.first()
        return iso_code

    def validate(self, data):
        country_iso_code = data["country_iso_code"]
        phone_number = data["phone_number"]

        try:
            wrapper = PhoneNumberWrapper.from_string(
                phone_number=phone_number, region=country_iso_code
            )
        except NumberParseException:
            raise serializers.ValidationError(
                {**self.default_error_messages}, "invalid_phone_number"
            )

        if not wrapper.is_valid():
            raise serializers.ValidationError(
                {**self.default_error_messages}, "invalid_phone_number"
            )

        self.context["intl_phone_number"] = wrapper.as_e164

        return super().validate(data)


class CreatePasscodeSerializer(AbstractPassCodeSerializer):
    def validate(self, data):
        data = super().validate(data)
        intl_phone_number = self.context["intl_phone_number"]

        can_process, next_passcode_on = PassCode.objects.can_create_passcode(
            intl_phone_number
        )

        if not can_process:
            raise UnprocessableEntityError(
                f"You can't send new OTP right now because of your multiple attempts. Please try again in {next_passcode_on} seconds.",
                "unprocessable_passcode",
            )

        return data

    def create(self, validated_data):
        code: PassCode = PassCode.create(self.context["intl_phone_number"])

        return code

    def to_representation(self, instance: PassCode):
        repr = {"next_passcode_on": instance.next_passcode_on}
        return repr


class VerifyPassCodeSerializer(AbstractPassCodeSerializer):
    code = serializers.CharField()

    def validate_code(self, code: str):
        if not is_valid_otp(code):
            raise serializers.ValidationError(_("Invalid Code"), "invalid_code")

        return code

    def validate(self, data):
        data = super().validate(data)

        intl_phone_number = self.context["intl_phone_number"]

        can_process, next_verif_attempt_on = PassCode.objects.can_verify(
            intl_phone_number
        )

        if not can_process:
            raise UnprocessableEntityError(
                f"You can't verify our OTP right now because of your multiple attempts. Please try again in {next_verif_attempt_on} seconds.",
                "unprocessable_passcode",
            )

        passcode: PassCode = PassCode.objects.get_last_code(intl_phone_number)

        if passcode is None:
            raise serializers.ValidationError(
                {"code": _("The code has not found")}, "code_not_found"
            )

        if passcode.key_expired:
            raise serializers.ValidationError(
                {"code": _("The code has been expired")}, "code_expired"
            )

        code = data.get("code")

        verified = passcode.verify(code)

        if not verified:
            raise serializers.ValidationError(
                {"code": _("The code you provided is invalid")}, "invalid_code"
            )

        return data

    def create(self, validated_data):
        account, created = Account.objects.get_or_create(
            intl_phone_number=self.context["intl_phone_number"],
            defaults={
                "phone_number": validated_data.get("phone_number"),
                "country_id": self.context.get("country").id,
            },
        )

        self.context["created"] = created

        return account

    def to_representation(self, instance: Account):
        account_infos = AccountDetailsSerializer(instance).data
        refresh = RefreshToken.for_user(instance)

        repr = {
            "account": {"created": self.context["created"], **account_infos},
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return repr


class AccountPaymentCodeSerializer(serializers.Serializer):
    payment_code = serializers.CharField()


class AccountOwnerSpecificInfos(serializers.Serializer):
    number = serializers.CharField()
    first_name = serializers.CharField(source="owner_first_name")
    last_name = serializers.CharField(source="owner_last_name")


class ReceiverAccountSerializer(AccountOwnerSpecificInfos):
    pass


class AccountDetailsSerializer(AccountOwnerSpecificInfos):
    pass


class PinCreationSerializer(serializers.Serializer):
    pin1 = serializers.CharField(validators=[pin_validator])
    pin2 = serializers.CharField(validators=[pin_validator])

    def validate(self, attrs):
        data = super().validate(attrs)

        if data["pin1"] != data["pin2"]:
            raise serializers.ValidationError(
                _("Pins do not match"), code="mismatch_pin"
            )

        return data

    def update(self, instance: Account, validated_data):
        instance.set_pin(validated_data["pin1"])
        return instance

    def to_representation(self, instance):
        return {}


class AccountBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ("balance",)
        model = Account


class CarrierBaseSerializer(serializers.Serializer):
    carrier_code = serializers.CharField()

    def validate_carrier_code(self, value):
        qs = SupportedMobileMoneyCarrier.objects.filter(code=value)
        if not qs.exists():
            raise exceptions.ValidationError(
                _("This carrier is not supported"), code="unsupported_carrier"
            )
        self.context["carrier"] = qs.first()

        return value


class AddPhoneNumberSerializer(CarrierBaseSerializer, CreatePasscodeSerializer):
    pass


class VerifyPhoneNumberSerializer(CarrierBaseSerializer, VerifyPassCodeSerializer):
    def create(self, validated_data):
        phonenumber = PhoneNumber.create(
            validated_data["phone_number"],
            self.context["carrier"].id,
            validated_data["account"].id,
        )

        return phonenumber

    def to_representation(self, instance: Account):
        return {}


class ModifyPINSerializer(PINSerializerMixin, PinCreationSerializer):
    pass
