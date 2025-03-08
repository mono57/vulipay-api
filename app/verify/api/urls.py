from django.urls import path

from app.verify.api.views import GenerateOTPView, VerifyOTPView

app_name = "verify"

urlpatterns = [
    path("generate/", GenerateOTPView.as_view(), name="generate_otp"),
    path("verify/", VerifyOTPView.as_view(), name="verify_otp"),
]
