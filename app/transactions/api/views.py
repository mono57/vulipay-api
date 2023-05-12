from rest_framework.generics import CreateAPIView

from app.accounts.permissions import IsAuthenticatedAccount
from app.transactions.api import serializers


class P2PTransactionCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.P2PTransactionSerializer

    def perform_create(self, serializer):
        serializer.save(payer_account=self.request.user)
