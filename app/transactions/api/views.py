from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework import exceptions
from app.accounts.permissions import IsAuthenticatedAccount
from app.transactions.api import serializers as t_serializers
from app.accounts.api import serializers as accounts_serializers
from app.transactions.models import Transaction


class P2PTransactionCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = t_serializers.P2PTransactionSerializer

    def perform_create(self, serializer):
        serializer.save(receiver_account=self.request.user)

class TransactionDetailsRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = t_serializers.TransactionDetailsSerializer
    queryset = Transaction.objects.select_related('receiver_account', 'payer_account')
    lookup_field = 'payment_code'

    def get(self, request, *args, **kwargs):
        payment_code = kwargs.get('payment_code', None)

        if bool(not payment_code or not Transaction.is_valid_payment_code(payment_code)):
            raise exceptions.ValidationError(_("Unknown vulipay payment code"), code='unknown_payment_code')

        return super().get(request, *args, **kwargs)
