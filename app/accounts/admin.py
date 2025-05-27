from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from app.accounts import models
from app.core.utils import AppModelAdmin


class UserAdmin(BaseUserAdmin):
    list_display = (
        "get_identifier",
        "full_name",
        "country",
        "account_type_badge",
        "is_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "country", "is_business")
    search_fields = ("phone_number", "email", "full_name")
    ordering = ("email", "phone_number")
    readonly_fields = ("pin",)

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "password", "pin")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "full_name",
                    "profile_picture",
                    "country",
                    "preferences",
                    "is_business",
                )
            },
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
                "fields": (
                    "email",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_business",
                ),
            },
        ),
    )

    def get_identifier(self, obj):
        if obj.phone_number:
            return obj.phone_number
        return obj.email

    get_identifier.short_description = "Identifier"

    def account_type_badge(self, obj):
        if obj.is_business:
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 4px 8px; '
                'border-radius: 4px; font-size: 0.8em;">Business</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 8px; '
                'border-radius: 4px; font-size: 0.8em;">Personal</span>'
            )

    account_type_badge.short_description = "Account Type"
    account_type_badge.admin_order_field = "is_business"


@admin.register(models.User)
class UserModelAdmin(UserAdmin):
    pass


@admin.register(models.AvailableCountry)
class AvailableCountryModelAdmin(admin.ModelAdmin):
    pass
