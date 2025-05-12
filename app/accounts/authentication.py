from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


class AppJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        # if user and (not user.full_name or not user.full_name.strip()):
        #     raise exceptions.AuthenticationFailed(
        #         _("User profile is incomplete. Please set your full name."),
        #         code="incomplete_profile",
        #     )

        return user


class AppJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "app.accounts.authentication.AppJWTAuthentication"
    name = "Bearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT authentication. Enter your token in the format: Bearer <token>",
        }
