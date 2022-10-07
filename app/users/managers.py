from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, phone_number, **kwargs):
        safe_phone_number = self.validate_phone_number(phone_number)

        user = self.model(phone_number=safe_phone_number, **kwargs)

        user.save()

        return user

    def validate_phone_number(self, phone_number):
        if not phone_number:
            raise ValueError(_("Phone number must be set"))

        return phone_number

    def create_superuser(self, email, password, **kwargs):
        if not email:
            raise ValueError(_("Email must be set"))

        user = self.model(email=self.normalize_email(email), **kwargs)
        user.set_password(password)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True

        user.save()

        return user
