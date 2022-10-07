from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from otp_auth.models import PhoneNumber
from users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("Email address"), unique=True, blank=True)
    phone_number = models.CharField(_("Phone number"), max_length=20)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @classmethod
    def get_or_create(cls, phone_number, country_iso_code):

        user, created = cls.objects.get_or_create(phone_number=phone_number)

        if not created:
            return user

        PhoneNumber.create(
            phone_number=phone_number,
            user=user,
            country_iso_code=country_iso_code,
            verified=True,
        )

        return user
