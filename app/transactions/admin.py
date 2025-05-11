from django import forms
from django.contrib import admin
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

    def clean_allowed_transactions(self):
        return self.cleaned_data["allowed_transactions"]


class PaymentMethodTypeAdmin(admin.ModelAdmin):
    form = PaymentMethodTypeAdminForm
    list_display = ("name", "code", "country", "get_allowed_transactions")

    def get_allowed_transactions(self, obj):
        if obj.allowed_transactions:
            return ", ".join(obj.allowed_transactions)
        return "-"

    get_allowed_transactions.short_description = "Allowed Transactions"


class PlatformWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "balance", "currency", "country", "created_on", "updated_on")
    list_filter = ("currency", "country")
    search_fields = ("currency", "country__name")
    readonly_fields = ("created_on", "updated_on", "balance")


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
admin.site.register(Wallet)
admin.site.register(PaymentMethodType, PaymentMethodTypeAdmin)
admin.site.register(PlatformWallet, PlatformWalletAdmin)
