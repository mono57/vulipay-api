from django.urls import path

from app.accounts.api.views import (
    AccountBalanceRetrieveAPIView,
    AccountInfoUpdateUpdateAPIView,
    AccountPaymentCodeRetrieveAPIView,
    AccountPaymentDetailsRetrieveAPIView,
    ModifyPINUpdateAPIView,
    PhoneNumberListCreateAPIView,
    PinCreationUpdateAPIView,
    UserFullNameUpdateView,
)

app_name = "accounts"

urlpatterns = [
    path(
        "<str:number>/payment-code",
        AccountPaymentCodeRetrieveAPIView.as_view(),
        name="accounts_payment_code",
    ),
    path(
        "<str:payment_code>/payment-details",
        AccountPaymentDetailsRetrieveAPIView.as_view(),
        name="accounts_payment_details",
    ),
    path(
        "pin/set",
        PinCreationUpdateAPIView.as_view(),
        name="accounts_set_pin",
    ),
    path(
        "balance",
        AccountBalanceRetrieveAPIView.as_view(),
        name="accounts_balance",
    ),
    path("pin/modify", ModifyPINUpdateAPIView.as_view(), name="accounts_modify_pin"),
    path("", AccountInfoUpdateUpdateAPIView.as_view(), name="accounts_update_infos"),
    path(
        "phonenumbers",
        PhoneNumberListCreateAPIView.as_view(),
        name="accounts_phonenumbers_list_create",
    ),
    path(
        "user/full-name", UserFullNameUpdateView.as_view(), name="user_full_name_update"
    ),
]
