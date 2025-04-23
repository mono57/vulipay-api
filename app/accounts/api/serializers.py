import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from app.accounts.models import AvailableCountry

User = get_user_model()
logger = logging.getLogger(__name__)


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

    def update(self, instance, validated_data):
        if "profile_picture" in validated_data and instance.profile_picture:
            old_picture_name = instance.profile_picture.name
            instance = super().update(instance, validated_data)

            if old_picture_name and instance.profile_picture.name != old_picture_name:
                try:
                    storage = instance.profile_picture.storage
                    storage_type = storage.__class__.__name__

                    if hasattr(storage, "exists") and hasattr(storage, "delete"):
                        if storage.exists(old_picture_name):
                            storage.delete(old_picture_name)
                            logger.info(
                                f"Deleted old profile picture: {old_picture_name}"
                            )
                        else:
                            logger.warning(
                                f"Old profile picture not found: {old_picture_name}"
                            )
                    else:
                        logger.info(
                            f"Skipping deletion for storage type: {storage_type}"
                        )

                except Exception as e:
                    logger.error(f"Error deleting old profile picture: {e}")
        else:
            instance = super().update(instance, validated_data)

        return instance


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
