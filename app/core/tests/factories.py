import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from app.accounts.models import AvailableCountry

User = get_user_model()


class AvailableCountryFactory(DjangoModelFactory):
    class Meta:
        model = AvailableCountry

    name = factory.Sequence(lambda n: f"Test Country {n}")
    dial_code = factory.Sequence(lambda n: f"{n + 100}")
    iso_code = factory.Sequence(lambda n: f"TC{n}")
    phone_number_regex = r"^\d{9}$"
    currency = "USD"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"9876{n:04d}")
    full_name = factory.Sequence(lambda n: f"Test User {n}")
    is_active = True

    @factory.post_generation
    def country(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.country = extracted
        else:
            # Create a default country if none was provided
            self.country = AvailableCountryFactory.create()
