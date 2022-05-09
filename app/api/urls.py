from django.urls import path, include


app_name = "api"

urlpatterns = [
    path("accounts/", include("accounts.api.urls", namespace="accounts_api"))
]
