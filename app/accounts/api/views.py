from django.conf import settings

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from app.accounts.api.serializers import PassCodeSerializer, VerifyPassCodeSerializer, AccountPaymentCodeSerializer
from app.accounts.models import Account


class PassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = PassCodeSerializer

class VerifyPassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = VerifyPassCodeSerializer

class AccountPaymentCodeRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = AccountPaymentCodeSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'number'
    queryset = Account.objects.all()

    def get_queryset(self):
        return super().get_queryset().values('payment_code')
