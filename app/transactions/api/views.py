import datetime
import logging
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import generics, permissions
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.api.mixins import ValidPINRequiredMixin
from app.core.utils.encryption import decrypt_data, encrypt_data
from app.core.utils.hashers import make_transaction_ref
from app.transactions.api import serializers
from app.transactions.models import (
    PaymentMethod,
    PaymentMethodType,
    PlatformWallet,
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)
from app.transactions.utils import compute_inclusive_amount

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Transactions"],
    operation_id="list_create_payment_methods",
    description="List and create payment methods",
    responses={
        200: serializers.PaymentMethodSerializer(many=True),
        201: serializers.PaymentMethodSerializer,
    },
    request=serializers.PaymentMethodSerializer,
    parameters=[
        OpenApiParameter(
            name="transaction_type",
            description="Filter payment methods by transaction type (P2P, MP, CO, CI)",
            required=False,
            type=str,
            enum=TransactionType.values,
            location=OpenApiParameter.QUERY,
        ),
    ],
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
    pagination_class = None

    def get_queryset(self):
        queryset = PaymentMethod.objects.filter(user=self.request.user)

        transaction_type = self.request.query_params.get("transaction_type")
        if transaction_type and transaction_type in TransactionType.values:
            queryset = queryset.filter(
                payment_method_type__allowed_transactions__contains=[transaction_type]
            )

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            payment_type = self.request.data.get("type")
            if payment_type == "card":
                return serializers.CardPaymentMethodSerializer
            elif payment_type == "mobile_money":
                return serializers.MobileMoneyPaymentMethodSerializer

        return self.serializer_class

    def get_serializer_context(self):
        context = super().get_serializer_context()
        transaction_type = self.request.query_params.get("transaction_type")
        if transaction_type and transaction_type in TransactionType.values:
            context["transaction_type"] = transaction_type
        return context


@extend_schema(
    tags=["Transactions"],
    operation_id="retrieve_update_delete_payment_method",
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
    operation_id="create_add_funds_transaction",
    description="Initiate a Cash In transaction from a payment method to a wallet. The transaction will include a calculated fee based on the payment method type's cash-in transaction fee.",
    responses={
        201: OpenApiResponse(
            description="Transaction created successfully",
            response=serializers.AddFundsTransactionSerializer,
        ),
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
    operation_id="add_funds_callback",
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
    permission_classes = [permissions.AllowAny]

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
            transaction.status = TransactionStatus.COMPLETED
            if transaction.to_wallet:
                transaction.to_wallet.deposit(transaction.amount)

            if processor_reference:
                transaction.notes = f"Processor reference: {processor_reference}"

            transaction.save()

            return Response(
                {"message": "Transaction completed successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            transaction.status = TransactionStatus.FAILED
            if failure_reason:
                transaction.notes = f"Failure reason: {failure_reason}"

            transaction.save()

            return Response(
                {"message": "Transaction marked as failed"},
                status=status.HTTP_200_OK,
            )


@extend_schema(
    tags=["Transactions"],
    operation_id="list_payment_method_types",
    description="List available payment method types with transaction fees for all transaction types",
    responses={
        200: serializers.PaymentMethodTypeSerializer(many=True),
    },
    parameters=[
        OpenApiParameter(
            name="transaction_type",
            description="Filter by allowed transaction type (P2P, MP, CO, CI)",
            required=False,
            type=str,
            enum=TransactionType.values,
        ),
    ],
)
class PaymentMethodTypeListAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.PaymentMethodTypeSerializer
    queryset = PaymentMethodType.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        transaction_type = self.request.query_params.get("transaction_type")

        user_country = getattr(self.request.user, "country", None)
        if user_country:
            queryset = queryset.filter(country=user_country)

        if transaction_type and transaction_type in TransactionType.values:
            queryset = queryset.filter(
                allowed_transactions__contains=[transaction_type]
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        transaction_type = self.request.query_params.get("transaction_type")
        if transaction_type and transaction_type in TransactionType.values:
            context["transaction_type"] = transaction_type
        return context


@extend_schema(
    tags=["Transactions"],
    operation_id="generate_payment_code",
    description="Generate a payment code for receiving funds. Returns encrypted user data including full name, email, phone number, target wallet ID, and currency.",
    responses={
        200: OpenApiResponse(
            description="Encrypted user data",
            response=inline_serializer(
                name="EncryptedDataResponse",
                fields={
                    "encrypted_data": drf_serializers.CharField(
                        help_text="Encrypted data including user details, wallet info, and currency"
                    ),
                },
            ),
        ),
        400: OpenApiResponse(
            description="Invalid amount format",
        ),
    },
    request=serializers.ReceiveFundsPaymentCodeSerializer,
    examples=[
        OpenApiExample(
            "Request with amount",
            value={"amount": 1000},
            request_only=True,
        ),
        OpenApiExample(
            "Request without amount",
            value={},
            request_only=True,
        ),
    ],
)
class ReceiveFundsPaymentCodeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = serializers.ReceiveFundsPaymentCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        wallet = (
            Wallet.objects.filter(user=user, wallet_type=WalletType.MAIN)
            .values("id", "currency")
            .first()
        )

        data = {
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "target_wallet_id": wallet["id"] if wallet else None,
            "transaction_type": TransactionType.P2P,
            "target_wallet_currency": wallet["currency"] if wallet else None,
        }

        amount = serializer.validated_data.get("amount")
        if amount is not None:
            data["amount"] = float(amount)

        encrypted_data = encrypt_data(data)
        return Response({"encrypted_data": encrypted_data}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Transactions"],
    operation_id="decrypt_user_data",
    description="Decrypt user data that was previously encrypted by the payment code generation endpoint.",
    responses={
        200: OpenApiResponse(
            description="Decrypted user data",
            response=inline_serializer(
                name="DecryptedDataResponse",
                fields={
                    "full_name": drf_serializers.CharField(),
                    "email": drf_serializers.CharField(),
                    "phone_number": drf_serializers.CharField(),
                    "target_wallet_id": drf_serializers.IntegerField(allow_null=True),
                    "amount": drf_serializers.FloatField(required=False),
                    "transaction_type": drf_serializers.ChoiceField(
                        choices=TransactionType.choices, required=False
                    ),
                    "target_wallet_currency": drf_serializers.CharField(
                        required=False,
                        help_text="Currency code of the target wallet (e.g., USD, EUR, XAF)",
                    ),
                },
            ),
        ),
        400: OpenApiResponse(
            description="Invalid encrypted data",
        ),
    },
    request=serializers.UserDataDecryptionSerializer,
    examples=[
        OpenApiExample(
            "Request with encrypted data",
            value={
                "encrypted_data": "base64_encoded_encrypted_string",
            },
            request_only=True,
        ),
    ],
)
class UserDataDecryptionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = serializers.UserDataDecryptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            encrypted_data = serializer.validated_data.get("encrypted_data")
            decrypted_data = decrypt_data(encrypted_data)

            return Response(decrypted_data, status=status.HTTP_200_OK)
        except Exception as e:
            logging.error(f"Error decrypting data: {e}")
            return Response(
                {"detail": "Invalid encrypted data"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(
    tags=["Transactions"],
    operation_id="process_transaction",
    description="Process a transaction using decrypted user data. Requires PIN verification.",
    responses={
        200: OpenApiResponse(
            description="Transaction processed successfully",
            response=inline_serializer(
                name="ProcessTransactionResponse",
                fields={
                    "transaction_reference": drf_serializers.CharField(),
                    "status": drf_serializers.CharField(),
                    "amount": drf_serializers.FloatField(),
                    "currency": drf_serializers.CharField(
                        help_text="Currency code of the transaction, same as provided in the request (e.g., USD, EUR, XAF)"
                    ),
                    "message": drf_serializers.CharField(),
                },
            ),
        ),
        400: OpenApiResponse(
            description="Invalid transaction data or currency mismatch"
        ),
        403: OpenApiResponse(description="Invalid PIN or unauthorized access"),
    },
    request=serializers.ProcessTransactionSerializer,
    examples=[
        OpenApiExample(
            "Process Transaction Request",
            value={
                "amount": 1000,
                "transaction_type": "P2P",
                "target_wallet_id": 1,
                "full_name": "John Doe",
                "email": "johndoe@example.com",
                "phone_number": "+237612345678",
                "currency": "XAF",
                "pin": "1234",  # Required for PIN validation
            },
            request_only=True,
        ),
    ],
)
class ProcessTransactionAPIView(ValidPINRequiredMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = serializers.ProcessTransactionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        with transaction.atomic():
            try:
                transaction_obj = Transaction.create_transaction(
                    transaction_type=data["transaction_type"],
                    amount=data["amount"],
                    status=TransactionStatus.PENDING,
                    source_wallet=data["source_wallet"],
                    target_wallet=data["target_wallet"],
                    notes=f"Transfer to {data['full_name']}",
                    calculated_fee=data["calculated_fee"],
                    charged_amount=data["charged_amount"],
                )

                data["source_wallet"].transfer(
                    data["target_wallet"], data["charged_amount"]
                )

                PlatformWallet.objects.collect_fees(
                    country=request.user.country, amount=data["calculated_fee"]
                )

                transaction_obj.set_as_COMPLETED()

                return Response(
                    {
                        "transaction_reference": transaction_obj.reference,
                        "status": transaction_obj.status,
                        "amount": data["amount"],
                        "currency": data["currency"],
                        "message": _("Transaction processed successfully"),
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                logger.error(f"Error processing transaction: {str(e)}")
                return Response(
                    {"detail": _("Error processing transaction")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


@extend_schema(
    tags=["Transactions"],
    operation_id="list_transactions",
    description="List transactions with pagination for lazy loading in mobile app",
    responses={
        200: serializers.TransactionSerializer(many=True),
    },
    parameters=[
        OpenApiParameter(
            name="status",
            description="Filter by transaction status",
            required=False,
            type=str,
            enum=TransactionStatus.values,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="type",
            description="Filter by transaction type (P2P, MP, CO, CI)",
            required=False,
            type=str,
            enum=TransactionType.values,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="from_date",
            description="Filter transactions from this date (YYYY-MM-DD)",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="to_date",
            description="Filter transactions to this date (YYYY-MM-DD)",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="limit",
            description="Number of records to return per page",
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="offset",
            description="Starting point for pagination",
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class TransactionListAPIView(ListAPIView):
    serializer_class = serializers.TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        user_wallets = Wallet.objects.filter(user=user)

        queryset = Transaction.objects.filter(
            models.Q(from_wallet__in=user_wallets)
            | models.Q(to_wallet__in=user_wallets)
        ).order_by("-created_on")

        status = self.request.query_params.get("status")
        transaction_type = self.request.query_params.get("type")
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")

        if status and status in TransactionStatus.values:
            queryset = queryset.filter(status=status)

        if transaction_type and transaction_type in TransactionType.values:
            queryset = queryset.filter(type=transaction_type)

        if from_date:
            try:
                from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
                queryset = queryset.filter(created_on__date__gte=from_date)
            except ValueError:
                pass

        if to_date:
            try:
                to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").date()
                queryset = queryset.filter(created_on__date__lte=to_date)
            except ValueError:
                pass

        return queryset


@extend_schema(
    tags=["Transactions"],
    operation_id="get_wallet_balance",
    description="Get a user's wallet balance by wallet type. If no wallet type is provided, returns the main wallet balance.",
    parameters=[
        OpenApiParameter(
            name="wallet_type",
            type=str,
            description="Wallet type (e.g., MAIN, BUSINESS). Defaults to MAIN if not provided.",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Wallet balance",
            response=inline_serializer(
                name="WalletBalanceResponse",
                fields={
                    "balance": drf_serializers.DecimalField(
                        max_digits=12, decimal_places=2
                    ),
                },
            ),
        ),
        404: OpenApiResponse(description="Wallet not found for the specified type"),
    },
)
class WalletBalanceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        wallet_type = request.query_params.get("wallet_type", WalletType.MAIN)

        try:
            wallet_balance = (
                Wallet.objects.filter(user=request.user, wallet_type=wallet_type)
                .values_list("balance", flat=True)
                .first()
            )

            if wallet_balance is None:
                return Response(
                    {"detail": _("Wallet not found for the specified type")},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response({"balance": wallet_balance}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving wallet balance: {str(e)}")
            return Response(
                {"detail": _("Error retrieving wallet balance")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
