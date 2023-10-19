from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, views
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView

from app.accounts.api.mixins import ValidPINRequiredMixin
from app.accounts.permissions import IsAuthenticatedAccount
from app.transactions.api import serializers
from app.transactions.models import Transaction, TransactionStatus


class P2PTransactionCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.P2PTransactionSerializer

    def perform_create(self, serializer):
        serializer.save(receiver_account=self.request.user)


class MPTransactionCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.MPTransactionSerializer

    def perform_create(self, serializer):
        serializer.save(payer_account=self.request.user)


class BaseTransactionRetrieveAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        payment_code = kwargs.get("payment_code", None)

        if bool(
            not payment_code or not Transaction.is_valid_payment_code(payment_code)
        ):
            raise exceptions.ValidationError(
                _("Unknown vulipay payment code"), code="unknown_payment_code"
            )

        return super().get(request, *args, **kwargs)


class TransactionDetailsRetrieveAPIView(
    BaseTransactionRetrieveAPIView, RetrieveAPIView
):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.TransactionDetailsSerializer
    queryset = Transaction.objects.select_related("receiver_account", "payer_account")
    lookup_field = "payment_code"


# Need to be tested
class BaseTransactionUpdateAPIView(UpdateAPIView):
    allowed_status = tuple()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)

        assert (
            isinstance(self.allowed_status, tuple) == True
            or isinstance(self.allowed_status, list) == True
        )

        assert len(self.allowed_status) > 0

        for status in self.allowed_status:
            if not obj.is_status_allowed(status):
                raise exceptions.PermissionDenied(
                    _("Status not allowed. Invalid Transaction Status"),
                    code="invalid_status",
                )


class TransactionPairingUpdateAPIView(
    BaseTransactionRetrieveAPIView, BaseTransactionUpdateAPIView
):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.TransactionPairingSerializer
    queryset = Transaction.objects.all()
    lookup_field = "payment_code"
    allowed_status = (TransactionStatus.INITIATED,)

    def perform_update(self, serializer):
        serializer.save(account=self.request.user)


class ValidateTransactionUpdateAPIView(
    ValidPINRequiredMixin, BaseTransactionUpdateAPIView
):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.ValidateTransactionSerializer
    queryset = Transaction.objects.select_related(
        "receiver_account", "payer_account"
    ).all()
    lookup_field = "reference"
    allowed_status = (TransactionStatus.PENDING,)


class CashOutTransactionCreateAPIView(ValidPINRequiredMixin, CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.CashOutTransactionSerializer
    queryset = Transaction.objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["account"] = self.request.user
        return ctx
