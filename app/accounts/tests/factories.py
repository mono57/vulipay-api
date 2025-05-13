import factory
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from factory import Faker as faker
from factory import django

from app.accounts.models import *


class UserFactory(django.DjangoModelFactory):
    class Meta:
        model = User

    full_name = faker("name")
    email = faker("email")
    phone_number = factory.Sequence(lambda n: f"+2376980497{n:02d}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create method to handle profile pictures"""
        if "profile_picture" not in kwargs:
            # Only create a test image if not explicitly provided
            kwargs["profile_picture"] = SimpleUploadedFile(
                name="test_image.jpg",
                content=b"",  # Empty content for testing
                content_type="image/jpeg",
            )
        return super()._create(model_class, *args, **kwargs)

    @classmethod
    def create_with_password(cls, password="password", **kwargs):
        user = cls.create(**kwargs)
        user.set_password(password)
        user.save()
        return user

    @classmethod
    def create_superuser(cls, **kwargs):
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        kwargs.setdefault("email", faker("email").generate({}))

        user = cls.create_with_password(**kwargs)
        return user


class AvailableCountryFactory(django.DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = factory.Sequence(lambda n: f"Country {n}")
    dial_code = factory.Sequence(lambda n: f"{237 + n}")
    iso_code = factory.Sequence(lambda n: f"C{n}")
    phone_number_regex = "^\\+\\d{3}\\d{8}$"
    currency = factory.Sequence(lambda n: f"CUR{n}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create method to handle flag field"""
        if "flag" not in kwargs:
            # Only create a test image if not explicitly provided
            kwargs["flag"] = SimpleUploadedFile(
                name="test_flag.png",
                content=b"",  # Empty content for testing
                content_type="image/png",
            )
        return super()._create(model_class, *args, **kwargs)
