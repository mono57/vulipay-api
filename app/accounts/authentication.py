from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


class AppJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if user and (not user.full_name or not user.full_name.strip()):
            raise exceptions.AuthenticationFailed(
                _("User profile is incomplete. Please set your full name."),
                code="incomplete_profile",
            )

        return user
