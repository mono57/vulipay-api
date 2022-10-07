from collections.abc import Sequence

from countries.models import *
from django.contrib import admin
from django.http import HttpRequest
from utils.admin import AppModelAdmin


@admin.register(AvailableCountry)
class AvailableCountryModelAdmin(AppModelAdmin):
    pass
