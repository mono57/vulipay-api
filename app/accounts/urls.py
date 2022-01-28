from django.urls import path

from accounts.views import (
    ConfirmCodeCreateAPIView,
    RegisterCreateAPIView,
    ResendConfirmationCodeAPIView
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterCreateAPIView.as_view(), name='register'),
    path('resend-code/', ResendConfirmationCodeAPIView.as_view(), name="resend-code"),
    path('confirm/', ConfirmCodeCreateAPIView.as_view(), name='confirm')
]
