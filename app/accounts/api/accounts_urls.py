from django.urls import path

from app.accounts.api.views import (
    AppTokenRefreshView,
    CountryListView,
    ProfilePictureConfirmationView,
    ProfilePicturePresignedUrlView,
    UserFullNameUpdateView,
    UserPINSetupView,
    UserPreferencesUpdateView,
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
        "user/preferences",
        UserPreferencesUpdateView.as_view(),
        name="user_preferences_update",
    ),
    path(
        "user/profile-picture",
        UserProfilePictureUpdateView.as_view(),
        name="user_profile_picture_update",
    ),
    path(
        "user/profile-picture/presigned-url",
        ProfilePicturePresignedUrlView.as_view(),
        name="profile_picture_presigned_url",
    ),
    path(
        "user/profile-picture/confirm",
        ProfilePictureConfirmationView.as_view(),
        name="profile_picture_confirmation",
    ),
    path("token/refresh/", AppTokenRefreshView.as_view(), name="token_refresh"),
    path("countries/", CountryListView.as_view(), name="country_list"),
    path("cache-health/", cache_health_check, name="cache_health"),
]
