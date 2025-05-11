from django import forms
from django.contrib import admin

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


# Register your models here.
admin.site.register(Transaction)
admin.site.register(TransactionFee)
admin.site.register(PaymentMethod)
admin.site.register(Wallet)
admin.site.register(PaymentMethodType, PaymentMethodTypeAdmin)
admin.site.register(PlatformWallet, PlatformWalletAdmin)
