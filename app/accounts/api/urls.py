from accounts.api.views import (ConfirmCodeCreateAPIView,
                                GenerateCodeCreateAPIView)
from django.urls import path

app_name = "accounts"

urlpatterns = [
    path("codes/", GenerateCodeCreateAPIView.as_view(), name="generate_code"),
    path("verify/", ConfirmCodeCreateAPIView.as_view(), name="verify_code"),
]
