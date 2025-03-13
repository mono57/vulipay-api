from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


class UserFullNameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(_("Full name cannot be empty."))
        return value.strip()
