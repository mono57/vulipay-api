from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from app.accounts import models
from app.core.utils import AppModelAdmin


class UserAdmin(BaseUserAdmin):
    list_display = (
        "get_identifier",
        "full_name",
        "country",
        "is_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "country")
    search_fields = ("phone_number", "email", "full_name")
    ordering = ("email", "phone_number")
    readonly_fields = ("pin",)

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "password", "pin")}),
        (
            _("Personal info"),
            {"fields": ("full_name", "profile_picture", "country", "preferences")},
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

    def get_identifier(self, obj):
        if obj.phone_number:
            return obj.phone_number
        return obj.email

    get_identifier.short_description = "Identifier"


@admin.register(models.User)
class UserModelAdmin(UserAdmin):
    pass


@admin.register(models.AvailableCountry)
class AvailableCountryModelAdmin(admin.ModelAdmin):
    pass
