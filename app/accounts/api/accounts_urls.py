from django.urls import path

from app.accounts.api.views import (
    AccountBalanceRetrieveAPIView,
    AccountPaymentCodeRetrieveAPIView,
    AccountPaymentDetailsRetrieveAPIView,
    ModifyPINUpdateAPIView,
    PassCodeCreateAPIView,
    PhoneNumberListCreateAPIView,
    PinCreationUpdateAPIView,
    VerifyPassCodeCreateAPIView,
    VerifyPhoneNumberCreateAPIView,
)

app_name = "accounts"

urlpatterns = [
    path(
        "passcodes",
        PassCodeCreateAPIView.as_view(),
        name="accounts_passcodes",
    ),
    path(
        "passcodes/verify",
        VerifyPassCodeCreateAPIView.as_view(),
        name="accounts_passcodes_verify",
    ),
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
    # path(
    #     "phonenumbers",
    #     AddPhoneNumberCreateAPIView.as_view(),
    #     name="accounts_add_phonenumbers",
    # ),
    path(
        "phonenumbers/verify",
        VerifyPhoneNumberCreateAPIView.as_view(),
        name="accounts_verify_phonenumbers",
    ),
    path("pin/modify", ModifyPINUpdateAPIView.as_view(), name="accounts_modify_pin"),
    path(
        "phonenumbers",
        PhoneNumberListCreateAPIView.as_view(),
        name="accounts_phonenumbers_list_create",
    ),
]
