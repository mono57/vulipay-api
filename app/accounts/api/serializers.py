from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from app.accounts.models import AvailableCountry

User = get_user_model()


class UserFullNameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Full name cannot be empty."))
        return value.strip()


class UserProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("profile_picture",)

    def validate_profile_picture(self, value):
        if value:
            # Validate file size - limit to 5MB
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    _("Image file size should not exceed 5MB.")
                )

            # Validate file type
            if not value.content_type.startswith("image/"):
                raise serializers.ValidationError(
                    _("Uploaded file is not a valid image.")
                )

        return value


class UserPINSetupSerializer(serializers.Serializer):
    pin1 = serializers.CharField(max_length=4, min_length=4, write_only=True)
    pin2 = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def _validate_pin(self, value):
        """
        Validate that the PIN is 4 digits.
        """
        if not value.isdigit():
            raise serializers.ValidationError(_("PIN must contain only digits."))
        if len(value) != 4:
            raise serializers.ValidationError(_("PIN must be exactly 4 digits."))
        return value

    def validate_pin1(self, value):
        return self._validate_pin(value)

    def validate_pin2(self, value):
        return self._validate_pin(value)

    def validate(self, data):
        """
        Check that pin1 and pin2 match.
        """
        if data["pin1"] != data["pin2"]:
            raise serializers.ValidationError(_("PINs do not match."))
        return data

    def update(self, instance, validated_data):
        instance.set_pin(validated_data["pin1"])
        return instance


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableCountry
        fields = ["id", "name", "dial_code", "iso_code", "currency"]
