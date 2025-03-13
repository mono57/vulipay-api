from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from app.accounts.api.views import UserFullNameUpdateView

app_name = "accounts"

urlpatterns = [
    path(
        "user/full-name", UserFullNameUpdateView.as_view(), name="user_full_name_update"
    ),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
