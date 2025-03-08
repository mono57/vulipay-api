from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from app.accounts.models import AvailableCountry
from app.verify.models import OTP


class GenerateOTPSerializer(serializers.Serializer):
    """Serializer for generating OTP."""

    phone_number = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    country_iso_code = serializers.CharField(required=False)
    channel = serializers.ChoiceField(choices=OTP.CHANNEL_CHOICES, default="sms")

    def validate(self, attrs):
        """Validate that either phone_number or email is provided."""
        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                _("Either phone_number or email must be provided.")
            )

        # If phone_number is provided, country_iso_code is required
        if attrs.get("phone_number") and not attrs.get("country_iso_code"):
            raise serializers.ValidationError(
                _("country_iso_code is required when phone_number is provided.")
            )

        # If phone_number and country_iso_code are provided, validate country
        if attrs.get("phone_number") and attrs.get("country_iso_code"):
            try:
                country = AvailableCountry.objects.get(
                    iso_code=attrs["country_iso_code"]
                )
                # Format the phone number with country code
                attrs["identifier"] = f"+{country.dial_code}{attrs['phone_number']}"
            except AvailableCountry.DoesNotExist:
                raise serializers.ValidationError(_("Invalid country_iso_code."))

        # If email is provided, use it as the identifier
        if attrs.get("email"):
            attrs["identifier"] = attrs["email"]

            # If channel is sms but only email is provided, switch to email
            if attrs.get("channel") == "sms" and not attrs.get("phone_number"):
                attrs["channel"] = "email"

        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP."""

    phone_number = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    country_iso_code = serializers.CharField(required=False)
    code = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate that either phone_number or email is provided."""
        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                _("Either phone_number or email must be provided.")
            )

        # If phone_number is provided, country_iso_code is required
        if attrs.get("phone_number") and not attrs.get("country_iso_code"):
            raise serializers.ValidationError(
                _("country_iso_code is required when phone_number is provided.")
            )

        # If phone_number and country_iso_code are provided, validate country
        if attrs.get("phone_number") and attrs.get("country_iso_code"):
            try:
                country = AvailableCountry.objects.get(
                    iso_code=attrs["country_iso_code"]
                )
                # Format the phone number with country code
                attrs["identifier"] = f"+{country.dial_code}{attrs['phone_number']}"
            except AvailableCountry.DoesNotExist:
                raise serializers.ValidationError(_("Invalid country_iso_code."))

        # If email is provided, use it as the identifier
        if attrs.get("email"):
            attrs["identifier"] = attrs["email"]

        # Validate code format
        if not attrs["code"].isdigit():
            raise serializers.ValidationError(
                {"code": _("Code must contain only digits.")}
            )

        return attrs
