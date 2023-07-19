from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("accounts/", include("app.accounts.api.accounts_urls", namespace="accounts")),
    path(
        "transactions/",
        include("app.transactions.api.transactions_urls", namespace="transactions"),
    ),
]
