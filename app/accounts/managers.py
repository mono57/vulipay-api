import datetime
import os
import random

from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import F, Manager, Q
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, email=None, password=None, **extra_fields):
        if not phone_number and not email:
            raise ValueError(
                _("User must have either a phone number or an email address")
            )

        if email:
            email = self.normalize_email(email)

        # Set default empty string for full_name if not provided
        extra_fields.setdefault("full_name", "")

        user = self.model(phone_number=phone_number, email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, phone_number=None, **extra_fields):
        if not email:
            raise ValueError(_("Email address is required for superuser"))

        if not password:
            raise ValueError(_("Password is required for superuser"))

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(phone_number, email, password, **extra_fields)

    def get_by_natural_key(self, identifier):
        try:
            return self.get(
                models.Q(email=identifier) | models.Q(phone_number=identifier)
            )
        except self.model.DoesNotExist:
            raise self.model.DoesNotExist(
                f"User with identifier {identifier} does not exist"
            )
