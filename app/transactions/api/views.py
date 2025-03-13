from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import exceptions, permissions
from rest_framework import serializers as drf_serializers
from rest_framework import status, views
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.api.mixins import ValidPINRequiredMixin
from app.accounts.permissions import IsAuthenticatedAccount
from app.core.utils import make_payment_code, make_transaction_ref
from app.transactions.api import serializers
from app.transactions.models import (
    PaymentMethod,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
)


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


class CashInTransactionCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = serializers.CashInTransactionSerializer
    queryset = Transaction.objects.all()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["account"] = self.request.user
        return ctx


@extend_schema(
    tags=["Payment Methods"],
    description="List and create payment methods",
    responses={
        200: serializers.PaymentMethodSerializer(many=True),
        201: serializers.PaymentMethodSerializer,
    },
    request=serializers.PaymentMethodSerializer,
    examples=[
        OpenApiExample(
            "Card Payment Method",
            value={
                "type": "card",
                "cardholder_name": "John Doe",
                "card_number": "4111 1111 1111 1111",
                "expiry_date": "12/2025",
                "cvv": "123",
                "billing_address": "123 Main St, City, Country",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Mobile Money Payment Method",
            value={
                "type": "mobile_money",
                "provider": "MTN Mobile Money",
                "mobile_number": "+237612345678",
            },
            request_only=True,
        ),
    ],
)
class PaymentMethodListCreateAPIView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            payment_type = self.request.data.get("type")
            if payment_type == "card":
                return serializers.CardPaymentMethodSerializer
            elif payment_type == "mobile_money":
                return serializers.MobileMoneyPaymentMethodSerializer

        return self.serializer_class


@extend_schema(
    tags=["Payment Methods"],
    description="Retrieve, update, and delete payment methods",
    responses={
        200: serializers.PaymentMethodSerializer,
        204: None,
    },
    parameters=[
        OpenApiParameter(
            name="pk",
            description="Payment method ID",
            required=True,
            type=int,
            location=OpenApiParameter.PATH,
        ),
    ],
    examples=[
        OpenApiExample(
            "Card Payment Method Update",
            value={
                "cardholder_name": "Updated Name",
                "billing_address": "Updated Address",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Mobile Money Payment Method Update",
            value={
                "provider": "Updated Provider",
                "mobile_number": "+237698765432",
            },
            request_only=True,
        ),
    ],
)
class PaymentMethodDetailAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            payment_method = self.get_object()
            if payment_method.type == "card":
                return serializers.CardPaymentMethodSerializer
            elif payment_method.type == "mobile_money":
                return serializers.MobileMoneyPaymentMethodSerializer

        return self.serializer_class


@extend_schema(
    tags=["Transactions"],
    description="Initiate a Cash In transaction from a payment method to a wallet",
    responses={
        201: serializers.AddFundsTransactionSerializer,
    },
    request=serializers.AddFundsTransactionSerializer,
    examples=[
        OpenApiExample(
            "Cash In Request",
            value={
                "amount": 1000,
                "payment_method_id": 1,
                "wallet_id": 1,
            },
            request_only=True,
        ),
    ],
)
class AddFundsTransactionCreateAPIView(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.AddFundsTransactionSerializer

    def perform_create(self, serializer):
        transaction = serializer.save()
        # Here you would typically call an external service to process the payment
        # For now, we just return the transaction details
        return transaction


@extend_schema(
    tags=["Transactions"],
    description="Callback endpoint for external payment processor to complete a Cash In transaction",
    responses={
        200: OpenApiResponse(description="Transaction successfully processed"),
        400: OpenApiResponse(description="Invalid request"),
        404: OpenApiResponse(description="Transaction not found"),
    },
    request=inline_serializer(
        name="CashInCallbackSerializer",
        fields={
            "transaction_reference": drf_serializers.CharField(),
            "status": drf_serializers.ChoiceField(choices=["success", "failed"]),
            "processor_reference": drf_serializers.CharField(required=False),
            "failure_reason": drf_serializers.CharField(required=False),
        },
    ),
)
class AddFundsCallbackAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # External service needs access

    def post(self, request, *args, **kwargs):
        transaction_reference = request.data.get("transaction_reference")
        transaction_status = request.data.get("status")
        processor_reference = request.data.get("processor_reference")
        failure_reason = request.data.get("failure_reason")

        if not transaction_reference or not transaction_status:
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction = Transaction.objects.get(
                reference=transaction_reference, type=TransactionType.CashIn
            )
        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if transaction_status == "success":
            # Process successful transaction
            transaction.status = TransactionStatus.COMPLETED
            if transaction.wallet:
                transaction.wallet.deposit(transaction.amount)

            # Add processor reference if provided
            if processor_reference:
                transaction.notes = f"Processor reference: {processor_reference}"

            transaction.save()

            return Response(
                {"message": "Transaction completed successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            # Process failed transaction
            transaction.status = TransactionStatus.FAILED
            if failure_reason:
                transaction.notes = f"Failure reason: {failure_reason}"

            transaction.save()

            return Response(
                {"message": "Transaction marked as failed"}, status=status.HTTP_200_OK
            )
