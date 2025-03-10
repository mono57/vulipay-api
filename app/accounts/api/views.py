from django.conf import settings
from rest_framework import generics, permissions

from app.accounts.api.mixins import AccountOwnerActionMixin, ValidPINRequiredMixin
from app.accounts.api.serializers import (
    AccountBalanceSerializer,
    AccountDetailsSerializer,
    AccountInfoUpdateModelSerializer,
    AccountPaymentCodeSerializer,
    ModifyPINSerializer,
    PinCreationSerializer,
    UserFullNameUpdateSerializer,
    VerifyPhoneNumberListItemSerializer,
)
from app.accounts.models import Account, PhoneNumber
from app.accounts.permissions import IsAuthenticatedAccount


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


class ModifyPINUpdateAPIView(
    ValidPINRequiredMixin, AccountOwnerActionMixin, generics.UpdateAPIView
):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = ModifyPINSerializer
    queryset = Account.objects.all()
    lookup_field = "number"


class PhoneNumberListCreateAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = VerifyPhoneNumberListItemSerializer

    def get_queryset(self):
        qs = PhoneNumber.objects.get_verify_phonenumbers(self.request.user).values(
            "number"
        )
        return qs


class AccountInfoUpdateUpdateAPIView(AccountOwnerActionMixin, generics.UpdateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = AccountInfoUpdateModelSerializer
    queryset = Account.objects.all()
    lookup_field = "number"


class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
