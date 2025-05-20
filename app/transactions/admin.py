from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from app.transactions.models import (
    PaymentMethod,
    PaymentMethodType,
    PlatformWallet,
    Transaction,
    TransactionFee,
    TransactionType,
    Wallet,
)


class PaymentMethodTypeAdminForm(forms.ModelForm):
    allowed_transactions = forms.MultipleChoiceField(
        choices=[(value, label) for value, label in TransactionType.choices],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = PaymentMethodType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.allowed_transactions:
            self.initial["allowed_transactions"] = self.instance.allowed_transactions
        if "logo" in self.fields:
            self.fields["logo"].required = True
        if "code" in self.fields:
            self.fields["code"].required = False
            self.fields["code"].help_text = _(
                "Will be automatically generated if left empty."
            )

    def clean_allowed_transactions(self):
        return self.cleaned_data["allowed_transactions"]

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if not logo and not self.instance.pk:
            raise forms.ValidationError(_("Logo image is required."))
        return logo

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise forms.ValidationError(_("Name is required."))
        return name

    def generate_code(self, name):
        import re

        # Convert to uppercase and replace spaces with underscores
        code = name.upper().replace(" ", "_")
        # Remove special characters
        code = re.sub(r"[^\w_]", "", code)

        # Ensure code is unique
        base_code = code
        counter = 1
        while (
            PaymentMethodType.objects.filter(code=code)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            code = f"{base_code}_{counter}"
            counter += 1

        return code

    def clean(self):
        cleaned_data = super().clean()
        # Check if logo is provided when editing an existing record
        if self.instance.pk and not cleaned_data.get("logo") and not self.instance.logo:
            self.add_error("logo", _("Logo image is required."))

        # Auto-generate code if empty
        name = cleaned_data.get("name")
        code = cleaned_data.get("code")

        if name and not code:
            cleaned_data["code"] = self.generate_code(name)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Generate code if it's still empty (fallback)
        if not instance.code and instance.name:
            instance.code = self.generate_code(instance.name)

        if commit:
            instance.save()
        return instance


class PaymentMethodTypeAdmin(admin.ModelAdmin):
    form = PaymentMethodTypeAdminForm
    list_display = (
        "name",
        "code",
        "country",
        "get_allowed_transactions",
        "get_logo_preview",
    )
    readonly_fields = ("get_logo_preview",)
    fieldsets = (
        (None, {"fields": ("name", "code", "country", "allowed_transactions")}),
        (
            _("Images"),
            {
                "fields": ("logo", "get_logo_preview"),
                "description": _(
                    "Upload logo for the payment method. Recommended size: 200x100px."
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk:  # Only make code readonly when editing
            readonly_fields.append("code")
        return readonly_fields

    def get_allowed_transactions(self, obj):
        if obj.allowed_transactions:
            return ", ".join(obj.allowed_transactions)
        return "-"

    get_allowed_transactions.short_description = "Allowed Transactions"

    def get_logo_preview(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" width="200" height="100" />')
        return "-"

    get_logo_preview.short_description = _("Logo Preview")


class PlatformWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "balance", "currency", "country", "created_on", "updated_on")
    list_filter = ("currency", "country")
    search_fields = ("currency", "country__name")
    readonly_fields = ("created_on", "updated_on", "balance")


class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "id",
        "balance",
        "wallet_type",
        "currency",
        "is_active",
        "created_on",
        "last_updated",
    )
    list_filter = ("wallet_type", "currency", "is_active")
    search_fields = ("user__email", "user__full_name", "currency")
    readonly_fields = ("created_on", "last_updated", "balance")
    raw_id_fields = ("user",)
    list_display_links = ("user",)


class TransactionFeeAdminForm(forms.ModelForm):
    class Meta:
        model = TransactionFee
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        fixed_fee = cleaned_data.get("fixed_fee")
        percentage_fee = cleaned_data.get("percentage_fee")

        if fixed_fee is None and percentage_fee is None:
            raise forms.ValidationError(
                _("Either fixed fee or percentage fee must be provided.")
            )

        return cleaned_data


class TransactionFeeAdmin(admin.ModelAdmin):
    form = TransactionFeeAdminForm
    list_display = (
        "name",
        "transaction_type",
        "payment_method_type",
        "country",
        "get_fee_display",
        "fee_priority",
    )
    list_filter = ("transaction_type", "fee_priority", "country", "payment_method_type")
    search_fields = (
        "name",
        "transaction_type",
        "payment_method_type__name",
        "country__name",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "transaction_type",
                    "country",
                    "payment_method_type",
                )
            },
        ),
        (
            _("Fee Details"),
            {
                "fields": ("fixed_fee", "percentage_fee", "fee_priority"),
                "description": _(
                    "Please provide either a fixed fee or a percentage fee. The fee priority will be automatically set based on which fee type is provided."
                ),
            },
        ),
    )

    radio_fields = {"fee_priority": admin.HORIZONTAL}

    def get_fee_display(self, obj):
        if obj.fixed_fee is not None:
            return f"Fixed: {obj.fixed_fee}"
        elif obj.percentage_fee is not None:
            return f"Percentage: {obj.percentage_fee}%"
        return "-"

    get_fee_display.short_description = "Fee"


# Register your models here.
admin.site.register(Transaction)
admin.site.register(TransactionFee, TransactionFeeAdmin)
admin.site.register(PaymentMethod)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(PaymentMethodType, PaymentMethodTypeAdmin)
admin.site.register(PlatformWallet, PlatformWalletAdmin)
