from django.conf import settings
from rest_framework import generics

from app.accounts.api.mixins import AccountOwnerActionMixin, ValidPINRequiredMixin
from app.accounts.api.serializers import (
    AccountBalanceSerializer,
    AccountDetailsSerializer,
    AccountPaymentCodeSerializer,
    AddPhoneNumberSerializer,
    CreatePasscodeSerializer,
    ModifyPINSerializer,
    PinCreationSerializer,
    VerifyPassCodeSerializer,
    VerifyPhoneNumberSerializer,
)
from app.accounts.models import Account
from app.accounts.permissions import IsAuthenticatedAccount


class PassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ["post"]
    serializer_class = CreatePasscodeSerializer


class VerifyPassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ["post"]
    serializer_class = VerifyPassCodeSerializer


class BaseAccountRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedAccount]
    lookup_field = "number"
    queryset = Account.objects.all()


class AccountPaymentCodeRetrieveAPIView(BaseAccountRetrieveAPIView):
    serializer_class = AccountPaymentCodeSerializer
    queryset = Account.objects.values("payment_code")


class AccountPaymentDetailsRetrieveAPIView(BaseAccountRetrieveAPIView):
    serializer_class = AccountDetailsSerializer
    lookup_field = "payment_code"
    queryset = Account.objects.values("number", "owner_first_name", "owner_last_name")


class PinCreationUpdateAPIView(AccountOwnerActionMixin, generics.UpdateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = PinCreationSerializer
    queryset = Account.objects.all()
    lookup_field = "number"


class AccountBalanceRetrieveAPIView(
    AccountOwnerActionMixin, BaseAccountRetrieveAPIView
):
    serializer_class = AccountBalanceSerializer


class AddPhoneNumberCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = AddPhoneNumberSerializer
    http_method_names = ["post"]


class VerifyPhoneNumberCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = VerifyPhoneNumberSerializer
    http_method_names = ["post"]

    def perform_create(self, serializer):
        return serializer.save(account=self.request.user)


class ModifyPINUpdateAPIView(
    ValidPINRequiredMixin, AccountOwnerActionMixin, generics.UpdateAPIView
):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = ModifyPINSerializer
    queryset = Account.objects.all()
    lookup_field = "number"
