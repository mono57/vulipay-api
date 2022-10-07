from countries.managers import AvailableCountryManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import AppModel


class AvailableCountry(AppModel):
    name = models.CharField(max_length=30)  # i.e Chad
    calling_code = models.CharField(max_length=5, unique=True)  # i.e 235
    iso_code = models.CharField(max_length=10, unique=True)  # i.e TD
    phone_number_regex = models.CharField(max_length=50)

    objects = AvailableCountryManager()

    def __str__(self):
        return f"({self.calling_code}) - {self.name} - {self.iso_code}"


class Currency(AppModel):
    iso_code = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    country = models.ForeignKey(AvailableCountry, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} - {self.iso_code} - {self.symbol}"


class NetworkProvider(AppModel):
    name = models.CharField(max_length=30, verbose_name=_("name"))

    def __str__(self):
        return self.name
