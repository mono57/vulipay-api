from django.urls import path

from app.accounts.api.views import (
    AppTokenRefreshView,
    UserFullNameUpdateView,
    UserPINSetupView,
)

app_name = "accounts"

urlpatterns = [
    path(
        "user/full-name", UserFullNameUpdateView.as_view(), name="user_full_name_update"
    ),
    path("user/pin-setup", UserPINSetupView.as_view(), name="user_pin_setup"),
    path("token/refresh/", AppTokenRefreshView.as_view(), name="token_refresh"),
]
