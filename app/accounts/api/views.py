from django.conf import settings

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from app.accounts.api import serializers
from app.accounts.models import Account
from app.accounts.permissions import IsAuthenticatedAccount


class PassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = serializers.CreatePasscodeSerializer

class VerifyPassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = serializers.VerifyPassCodeSerializer

class AccountPaymentCodeRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.AccountPaymentCodeSerializer
    lookup_field = 'number'
    queryset = Account.objects.all()

    def get_queryset(self):
        return super().get_queryset().values('payment_code')


class AccountPaymentDetailsRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.AccountDetailsSerializer
    lookup_field = 'payment_code'
    queryset = Account.objects.values('number', 'owner_first_name', 'owner_last_name')

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)