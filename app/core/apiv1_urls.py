from django.urls import include, path

from app.accounts.api import views as accounts_views

app_name = "api"

urlpatterns = [
    path('accounts/passcodes', accounts_views.PassCodeCreateAPIView.as_view(), name="accounts_passcodes"),
]
