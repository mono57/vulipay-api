from django.urls import path

from app.transactions.api.views import (
    AddFundsCallbackAPIView,
    AddFundsTransactionCreateAPIView,
    PaymentMethodDetailAPIView,
    PaymentMethodListCreateAPIView,
    PaymentMethodTypeListAPIView,
    ProcessTransactionAPIView,
    ReceiveFundsPaymentCodeAPIView,
    TransactionListAPIView,
    UserDataDecryptionAPIView,
    WalletBalanceAPIView,
)

app_name = "transactions"

urlpatterns = [
    path(
        "cash-in",
        AddFundsTransactionCreateAPIView.as_view(),
        name="transactions_cash_in",
    ),
    path(
        "cash-in/callback",
        AddFundsCallbackAPIView.as_view(),
        name="transactions_cash_in_callback",
    ),
    path(
        "payment-methods/",
        PaymentMethodListCreateAPIView.as_view(),
        name="payment_methods_list_create",
    ),
    path(
        "payment-methods/<int:pk>/",
        PaymentMethodDetailAPIView.as_view(),
        name="payment_method_detail",
    ),
    path(
        "payment-method-types/",
        PaymentMethodTypeListAPIView.as_view(),
        name="payment-method-types-list",
    ),
    path(
        "payment-code/",
        ReceiveFundsPaymentCodeAPIView.as_view(),
        name="receive-funds-payment-code",
    ),
    path(
        "payment-code/decrypt/",
        UserDataDecryptionAPIView.as_view(),
        name="decrypt-user-data",
    ),
    path(
        "process",
        ProcessTransactionAPIView.as_view(),
        name="process-transaction",
    ),
    path(
        "list",
        TransactionListAPIView.as_view(),
        name="transactions-list",
    ),
    path(
        "wallet/balance",
        WalletBalanceAPIView.as_view(),
        name="wallet-balance",
    ),
]
