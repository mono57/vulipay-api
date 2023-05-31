from django.urls import path

from app.accounts.api import views as accounts_views
from app.transactions.api import views as transactions_views

app_name = "api"

urlpatterns = [
    path(
        "accounts/passcodes",
        accounts_views.PassCodeCreateAPIView.as_view(),
        name="accounts_passcodes",
    ),
    path(
        "accounts/passcodes/verify",
        accounts_views.VerifyPassCodeCreateAPIView.as_view(),
        name="accounts_passcodes_verify",
    ),
    path(
        "accounts/<str:number>/payment-code",
        accounts_views.AccountPaymentCodeRetrieveAPIView.as_view(),
        name="accounts_payment_code",
    ),
    path(
        "accounts/<str:payment_code>/payment-details",
        accounts_views.AccountPaymentDetailsRetrieveAPIView.as_view(),
        name="accounts_payment_details",
    ),
    path(
        "transactions/P2P",
        transactions_views.P2PTransactionCreateAPIView.as_view(),
        name="transactions_p2p_transactions",
    ),
    path(
        "transactions/MP",
        transactions_views.MPTransactionCreateAPIView.as_view(),
        name="transactions_mp_transactions",
    ),
    path(
        "transactions/<str:payment_code>/details",
        transactions_views.TransactionDetailsRetrieveAPIView.as_view(),
        name="transactions_transaction_details",
    ),
]
