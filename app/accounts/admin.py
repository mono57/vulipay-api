from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from app.accounts import models
from app.core.utils import AppModelAdmin


class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "phone_number",
        "full_name",
        "country",
        "is_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "country")
    search_fields = ("phone_number", "email", "full_name")
    ordering = ("email", "phone_number")

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "password")}),
        (
            _("Personal info"),
            {"fields": ("full_name", "profile_picture", "country")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone_number", "password1", "password2"),
            },
        ),
    )


@admin.register(models.User)
class UserModelAdmin(UserAdmin):
    pass


@admin.register(models.AvailableCountry)
class AvailableCountryModelAdmin(admin.ModelAdmin):
    pass
