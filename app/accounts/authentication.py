from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import Token

User = get_user_model()


class AppJWTAuthentication(JWTAuthentication):
    def __init__(self):
        super().__init__()
        self.user_model = User

    def get_user(self, validated_token: Token):
        try:
            user = super().get_user(validated_token)
        except AuthenticationFailed as ex:
            # need to be customize
            if ex.default_code == "user_not_found":
                raise AuthenticationFailed(
                    {"detail": _("User not found"), "code": "user_not_found"}
                )
            raise AuthenticationFailed(
                {"detail": _("User is inactive"), "code": "user_inactive"}
            )

        return user
