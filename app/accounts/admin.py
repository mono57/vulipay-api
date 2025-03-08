from django.contrib import admin

from app.accounts import models
from app.core.utils import AppModelAdmin


@admin.register(models.Account)
class AccountModelAdmin(admin.ModelAdmin):
    pass


@admin.register(models.PhoneNumber)
class PhoneNumberModelAdmin(admin.ModelAdmin):
    pass


@admin.register(models.AvailableCountry)
class AvailableCountryModelAdmin(admin.ModelAdmin):
    pass
