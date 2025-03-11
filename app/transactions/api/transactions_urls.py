from django.urls import path

from app.transactions.api.views import (
    CashInTransactionCreateAPIView,
    CashOutTransactionCreateAPIView,
    MPTransactionCreateAPIView,
    P2PTransactionCreateAPIView,
    PaymentMethodDetailAPIView,
    PaymentMethodListCreateAPIView,
    TransactionDetailsRetrieveAPIView,
    TransactionPairingUpdateAPIView,
    ValidateTransactionUpdateAPIView,
)

app_name = "transactions"

urlpatterns = [
    path(
        "P2P",
        P2PTransactionCreateAPIView.as_view(),
        name="transactions_p2p_transactions",
    ),
    path(
        "MP",
        MPTransactionCreateAPIView.as_view(),
        name="transactions_mp_transactions",
    ),
    path(
        "CO",
        CashOutTransactionCreateAPIView.as_view(),
        name="transactions_co_transactions",
    ),
    path(
        "CI",
        CashInTransactionCreateAPIView.as_view(),
        name="transactions_ci_transactions",
    ),
    path(
        "<str:payment_code>/details",
        TransactionDetailsRetrieveAPIView.as_view(),
        name="transactions_transaction_details",
    ),
    path(
        "<str:reference>/validate",
        ValidateTransactionUpdateAPIView.as_view(),
        name="transactions_transaction_validate",
    ),
    path(
        "<str:payment_code>/pairing",
        TransactionPairingUpdateAPIView.as_view(),
        name="transactions_transaction_pairing",
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
]
