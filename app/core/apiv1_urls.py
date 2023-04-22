from django.urls import include, path

from app.accounts.api import views as accounts_views

app_name = "api"

urlpatterns = [
    path(
        'accounts/passcodes',
        accounts_views.PassCodeCreateAPIView.as_view(),
        name="accounts_passcodes"),
    path(
        'accounts/passcodes/verify',
        accounts_views.VerifyPassCodeCreateAPIView.as_view(),
        name="accounts_passcodes_verify"),
    path(
        'accounts/<str:number>/payment-code',
        accounts_views.AccountPaymentCodeRetrieveAPIView.as_view(),
        name="accounts_payment_code"),
]
