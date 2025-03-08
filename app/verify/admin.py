from django.contrib import admin

from app.verify.models import OTP


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        "identifier",
        "code",
        "channel",
        "is_used",
        "is_expired",
        "expires_at",
        "created_on",
    )
    list_filter = ("channel", "is_used", "is_expired")
    search_fields = ("identifier", "code")
    readonly_fields = ("created_on", "updated_on")
    fieldsets = (
        (None, {"fields": ("identifier", "code", "channel")}),
        (
            "Status",
            {
                "fields": (
                    "is_used",
                    "is_expired",
                    "expires_at",
                    "used_at",
                    "attempt_count",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_on", "updated_on")}),
    )
