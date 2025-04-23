from django.urls import path

from app.accounts.api.views import (
    AppTokenRefreshView,
    CountryListView,
    UserFullNameUpdateView,
    UserPINSetupView,
    UserProfilePictureUpdateView,
    cache_health_check,
)

app_name = "accounts"

urlpatterns = [
    path(
        "user/full-name", UserFullNameUpdateView.as_view(), name="user_full_name_update"
    ),
    path("user/pin-setup", UserPINSetupView.as_view(), name="user_pin_setup"),
    path(
        "user/profile-picture",
        UserProfilePictureUpdateView.as_view(),
        name="user_profile_picture_update",
    ),
    path("token/refresh/", AppTokenRefreshView.as_view(), name="token_refresh"),
    path("countries/", CountryListView.as_view(), name="country_list"),
    path("cache-health/", cache_health_check, name="cache_health"),
]
