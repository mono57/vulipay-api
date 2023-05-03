from django.utils.translation import gettext_lazy as _

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import Token

from app.accounts.models import Account

class AppJWTAuthentication(JWTAuthentication):
    def __init__(self):
        super().__init__()
        self.user_model = Account

    def get_user(self, validated_token: Token):
        try:
            account = super().get_user(validated_token)
        except AuthenticationFailed as ex:
            # need to be customize
            if ex.default_code == 'user_not_found':
                raise AuthenticationFailed({"detail": _("Account not founnd"), "code": "account_not_found"})
            raise AuthenticationFailed({"detail": _("Account is inactive"), "code": "account_inactive"})

        return account