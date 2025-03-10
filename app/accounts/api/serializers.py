from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from phonenumber_field.phonenumber import PhoneNumber as PhoneNumberWrapper
from phonenumbers import NumberParseException
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import (
    Account,
    AvailableCountry,
    PhoneNumber,
    SupportedMobileMoneyCarrier,
)
from app.accounts.validators import pin_validator

User = get_user_model()


class PINSerializerMixin:
    pin = serializers.CharField()


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
        pin1 = attrs.get("pin1")
        pin2 = attrs.get("pin2")

        if pin1 != pin2:
            raise serializers.ValidationError(
                {"pin2": _("PIN codes don't match")}, "pin_mismatch"
            )

        return attrs

    def update(self, instance: Account, validated_data):
        instance.set_pin(validated_data.get("pin1"))
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
            raise serializers.ValidationError(
                _("The carrier you provided is not supported")
            )

        self.context["carrier"] = qs.first()

        return value


class ModifyPINSerializer(PINSerializerMixin, PinCreationSerializer):
    pass


class SupportedCarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportedMobileMoneyCarrier
        fields = ["name", "code", "flag"]


class PhoneNumberSerializer(serializers.ModelSerializer):
    carrier = SupportedCarrierSerializer()

    class Meta:
        model = PhoneNumber
        fields = ["number", "carrier"]


# class AccountInfoTransactionHistorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Account
#         fields = ["first_name", "last_name"]


class PhoneNumberTransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ["number"]


class VerifyPhoneNumberListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ["number"]


class AccountInfoUpdateModelSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="owner_first_name")
    last_name = serializers.CharField(source="owner_last_name")

    class Meta:
        model = Account
        fields = ("first_name", "last_name")


class UserFullNameUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a user's full name.
    """

    class Meta:
        model = User
        fields = ("full_name",)

    def validate_full_name(self, value):
        """
        Validate that the full_name is not empty.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Full name cannot be empty.")
        return value.strip()
