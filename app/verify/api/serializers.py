from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import AvailableCountry
from app.verify.models import OTP

User = get_user_model()


class GenerateOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=False, help_text="Phone number to send the OTP to"
    )
    email = serializers.EmailField(
        required=False, help_text="Email address to send the OTP to"
    )
    country_iso_code = serializers.CharField(
        required=False, help_text="ISO code of the country (e.g., 'CM' for Cameroon)"
    )
    channel = serializers.ChoiceField(
        choices=OTP.CHANNEL_CHOICES,
        default="sms",
        help_text="Channel to send the OTP through (sms, email, whatsapp)",
    )

    def validate(self, attrs):
        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                _("Either phone_number or email must be provided.")
            )

        if attrs.get("phone_number") and not attrs.get("country_iso_code"):
            raise serializers.ValidationError(
                _("country_iso_code is required when phone_number is provided.")
            )

        if attrs.get("phone_number") and attrs.get("country_iso_code"):
            try:
                country = AvailableCountry.objects.get(
                    iso_code=attrs["country_iso_code"]
                )
                attrs["identifier"] = f"+{country.dial_code}{attrs['phone_number']}"
            except AvailableCountry.DoesNotExist:
                raise serializers.ValidationError(_("Invalid country_iso_code."))

        if attrs.get("email"):
            attrs["identifier"] = attrs["email"]

            if attrs.get("channel") == "sms" and not attrs.get("phone_number"):
                attrs["channel"] = "email"

        return attrs

    def generate_otp(self):
        identifier = self.validated_data["identifier"]
        channel = self.validated_data["channel"]

        return OTP.generate(identifier, channel)


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=False, help_text="Phone number the OTP was sent to"
    )
    email = serializers.EmailField(
        required=False, help_text="Email address the OTP was sent to"
    )
    country_iso_code = serializers.CharField(
        required=False, help_text="ISO code of the country (e.g., 'CM' for Cameroon)"
    )
    code = serializers.CharField(required=True, help_text="OTP code to verify")

    def validate(self, attrs):
        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                _("Either phone_number or email must be provided.")
            )

        if attrs.get("phone_number") and not attrs.get("country_iso_code"):
            raise serializers.ValidationError(
                _("country_iso_code is required when phone_number is provided.")
            )

        if attrs.get("phone_number") and attrs.get("country_iso_code"):
            try:
                country = AvailableCountry.objects.get(
                    iso_code=attrs["country_iso_code"]
                )
                attrs["identifier"] = f"+{country.dial_code}{attrs['phone_number']}"
            except AvailableCountry.DoesNotExist:
                raise serializers.ValidationError(_("Invalid country_iso_code."))

        if attrs.get("email"):
            attrs["identifier"] = attrs["email"]

        if not attrs["code"].isdigit():
            raise serializers.ValidationError(
                {"code": _("Code must contain only digits.")}
            )

        return attrs

    def verify_otp(self):
        identifier = self.validated_data["identifier"]
        code = self.validated_data["code"]
        country_iso_code = self.validated_data.get("country_iso_code")

        otp = OTP.objects.get_active_otp(identifier)

        if not otp:
            return {
                "success": False,
                "message": "No active OTP found. Please request a new code.",
            }

        if otp.verify(code):
            user, created = User.objects.get_or_create(email=identifier)

            # Set the country if country_iso_code is provided
            if country_iso_code:
                try:
                    country = AvailableCountry.objects.get(iso_code=country_iso_code)
                    user.country = country
                    user.save()
                except AvailableCountry.DoesNotExist:
                    pass  # If country doesn't exist, continue without setting it

            refresh = RefreshToken.for_user(user)

            return {
                "success": True,
                "message": "OTP verified successfully.",
                "created": created,
                "user": {
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "country": user.country.name if user.country else None,
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }
        else:
            from django.conf import settings

            max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 3)
            remaining_attempts = max_attempts - otp.attempt_count

            if remaining_attempts <= 0:
                return {
                    "success": False,
                    "message": "Maximum verification attempts reached. Please request a new code.",
                }
            else:
                return {
                    "success": False,
                    "message": f"Invalid code. {remaining_attempts} attempts remaining.",
                }
