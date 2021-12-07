from django.urls import path
from accounts.views import ConfirmCodeCreateAPIView, RegisterCreateAPIView


app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterCreateAPIView.as_view(), name='register'),
    path('confirm/', ConfirmCodeCreateAPIView.as_view(), name='confirm')
]
