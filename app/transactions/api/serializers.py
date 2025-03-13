import calendar
import datetime
import re

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import exceptions, serializers

from app.accounts.api.serializers import AccountDetailsSerializer, PINSerializerMixin
from app.accounts.models import Account, AvailableCountry, PhoneNumber
from app.core.utils import AppAmountField
from app.core.utils.hashers import make_payment_code, make_transaction_ref
from app.transactions.models import (
    PaymentMethod,
    PaymentMethodType,
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)


class BasePaymentTransactionSerializer(serializers.Serializer):
    amount = AppAmountField()


class P2PTransactionSerializer(BasePaymentTransactionSerializer):
    def create(self, validated_data) -> Transaction:
        transaction = Transaction.create_P2P_transaction(**validated_data)
        return transaction

    def to_representation(self, instance: Transaction):
        repr = {
            "payment_code": instance.payment_code,
        }

        return repr


class MPTransactionSerializer(BasePaymentTransactionSerializer):
    receiver_account = serializers.CharField()

    def validate_receiver_account(self, account_number):
        account_qs = Account.objects.filter(number=account_number)

        if not account_qs.exists():
            raise serializers.ValidationError(
                _("Account not found"), code="account_not_found"
            )

        receiver_account = account_qs.first()

        self.context["receiver_account"] = receiver_account

        return receiver_account

    def create(self, validated_data) -> Transaction:
        transaction = Transaction.create_MP_transaction(**validated_data)
        return transaction

    def to_representation(self, instance):
        repr = TransactionDetailsSerializer(instance).data

        return repr


class TransactionDetailsSerializer(serializers.ModelSerializer):
    receiver_account = AccountDetailsSerializer()
    payer_account = AccountDetailsSerializer()

    class Meta:
        model = Transaction
        fields = (
            "reference",
            "amount",
            "status",
            "type",
            "charged_amount",
            "calculated_fee",
            "payer_account",
            "receiver_account",
        )


class BaseBalanceValidationSerializerMixin:
    def update(self, instance: Transaction, validated_data):
        account: Account = validated_data.get("account")
        charge_amount = instance.get_inclusive_amount(account.country)
        code = account.check_balance(charge_amount)

        if code == -1:
            raise exceptions.PermissionDenied(
                _("Insufficient balance"), code="insufficient_balance"
            )

        return instance

    def to_representation(self, instance):
        repr = TransactionDetailsSerializer(instance=instance).data
        return repr


class ValidateTransactionSerializer(
    PINSerializerMixin, BaseBalanceValidationSerializerMixin, serializers.Serializer
):
    def update(self, instance, validated_data):
        validated_data.setdefault("account", instance.payer_account)

        instance: Transaction = super().update(instance, validated_data)

        instance.perform_payment()

        return instance


class TransactionPairingSerializer(
    BaseBalanceValidationSerializerMixin, serializers.Serializer
):
    def update(self, instance: Transaction, validated_data):
        instance = super().update(instance, validated_data)

        instance.pair(validated_data.get("account"))

        return instance


class CashInCashOutBaseSerializerMixin(serializers.Serializer):
    intl_phone_number = serializers.CharField()
    amount = AppAmountField()

    def validate_intl_phone_number(self, intl_phone_number):
        from_account = self.context.get("account")

        verified_phone_number = PhoneNumber.objects.phone_number_exists(
            from_account, intl_phone_number
        )
        if not verified_phone_number:
            raise serializers.ValidationError(
                _("Phone number is not verified"), code="unverified_phone_number"
            )

        self.context["verified_phone_number"] = verified_phone_number

        return intl_phone_number

    def to_representation(self, instance):
        return {}


class CashOutTransactionSerializer(
    PINSerializerMixin, CashInCashOutBaseSerializerMixin
):
    # TODO: Refactor compute inclusive amount business logic
    @transaction.atomic
    def create(self, validated_data):
        from_account = self.context["account"]
        to_phone_number = self.context["verified_phone_number"]

        transaction = Transaction.create_CO_transaction(
            amount=validated_data.get("amount"),
            from_account=from_account,
            to_phone_number=to_phone_number,
        )

        charge_amount = transaction.get_inclusive_amount(from_account.country)
        code = from_account.check_balance(charge_amount)

        if code == -1:
            raise exceptions.PermissionDenied(
                _("Insufficient balance"), code="insufficient_balance"
            )

        # Send CO request to queue

        return transaction


class CashInTransactionSerializer(CashInCashOutBaseSerializerMixin):
    @transaction.atomic
    def create(self, validated_data):
        account = self.context["account"]
        verified_phone_number = self.context["verified_phone_number"]

        transaction = Transaction.create_CI_transaction(
            amount=validated_data.get("amount"),
            to_account=account,
            from_phone_number=verified_phone_number,
        )

        charge_amount = transaction.get_inclusive_amount(account.country)
        # send CI request to queue

        return transaction


@extend_schema_serializer(component_name="PaymentMethod")
class PaymentMethodSerializer(serializers.ModelSerializer):
    payment_method_type = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethodType.objects.all(),
        required=False,
        write_only=True,
        help_text="ID of the payment method type",
    )
    cash_in_transaction_fee = serializers.SerializerMethodField(
        help_text="Transaction fee for cash in operations"
    )
    cash_out_transaction_fee = serializers.SerializerMethodField(
        help_text="Transaction fee for cash out operations"
    )
    payment_method_type_name = serializers.SerializerMethodField(
        help_text="Name of the payment method type"
    )

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "type",
            "default_method",
            "cardholder_name",
            "masked_card_number",
            "expiry_date",
            "provider",
            "mobile_number",
            "payment_method_type",
            "payment_method_type_name",
            "cash_in_transaction_fee",
            "cash_out_transaction_fee",
        ]
        read_only_fields = [
            "id",
            "payment_method_type_name",
            "cash_in_transaction_fee",
            "cash_out_transaction_fee",
        ]

    def get_payment_method_type(self, obj):
        # First try to get the payment method type directly from the database
        # This would work if the payment method was created with a payment_method_type
        payment_method_type_id = getattr(obj, "payment_method_type_id", None)
        if payment_method_type_id:
            try:
                return PaymentMethodType.objects.get(id=payment_method_type_id)
            except PaymentMethodType.DoesNotExist:
                pass

        # If that doesn't work, try to infer the type based on the code pattern
        if obj.type == "card":
            return PaymentMethodType.objects.filter(code__startswith="CARD").first()
        elif obj.type == "mobile_money" and obj.provider:
            # Try to match by provider name
            provider_words = obj.provider.upper().split()
            for word in provider_words:
                if len(word) > 2:  # Skip short words like "OF", "THE", etc.
                    matching_type = PaymentMethodType.objects.filter(
                        code__contains=word
                    ).first()
                    if matching_type:
                        return matching_type

            # If no match by provider words, try a generic mobile money type
            return PaymentMethodType.objects.filter(code__startswith="MOBILE").first()

        return None

    def get_cash_in_transaction_fee(self, obj):
        payment_method_type = self.get_payment_method_type(obj)
        return (
            payment_method_type.cash_in_transaction_fee if payment_method_type else None
        )

    def get_cash_out_transaction_fee(self, obj):
        payment_method_type = self.get_payment_method_type(obj)
        return (
            payment_method_type.cash_out_transaction_fee
            if payment_method_type
            else None
        )

    def get_payment_method_type_name(self, obj):
        payment_method_type = self.get_payment_method_type(obj)
        return payment_method_type.name if payment_method_type else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.type == "mobile_money":
            representation.pop("cardholder_name", None)
            representation.pop("masked_card_number", None)
            representation.pop("expiry_date", None)

        if instance.type == "card":
            representation.pop("provider", None)
            representation.pop("mobile_number", None)

        return representation


@extend_schema_serializer(component_name="CardPaymentMethod")
class CardPaymentMethodSerializer(serializers.ModelSerializer):
    card_number = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Card number (will be masked in responses)",
    )
    cvv = serializers.CharField(
        write_only=True, required=True, help_text="Card verification value (3-4 digits)"
    )
    payment_method_type = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethodType.objects.filter(code__startswith="CARD"),
        required=True,
        write_only=True,
        help_text="ID of the card payment method type",
    )

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "default_method",
            "cardholder_name",
            "card_number",
            "masked_card_number",
            "expiry_date",
            "cvv",
            "cvv_hash",
            "billing_address",
            "payment_method_type",
        ]
        read_only_fields = ["id", "masked_card_number", "cvv_hash"]
        extra_kwargs = {
            "cardholder_name": {
                "required": True,
                "help_text": "Name of the cardholder",
            },
            "expiry_date": {
                "required": True,
                "help_text": "Card expiry date in MM/YYYY format",
            },
            "billing_address": {
                "required": True,
                "help_text": "Billing address associated with the card",
            },
            "default_method": {
                "help_text": "Whether this is the default payment method"
            },
        }

    def validate_card_number(self, value):
        card_number = value.replace(" ", "").replace("-", "")

        if not card_number.isdigit() or not (13 <= len(card_number) <= 19):
            raise serializers.ValidationError("Invalid card number format.")

        return card_number

    def validate_cvv(self, value):
        if not value.isdigit() or not (3 <= len(value) <= 4):
            raise serializers.ValidationError("CVV must be 3 or 4 digits.")

        return value

    def validate_expiry_date(self, value):
        if not re.match(r"^(0[1-9]|1[0-2])/20[2-9][0-9]$", value):
            raise serializers.ValidationError("Expiry date must be in MM/YYYY format.")

        try:
            month, year = value.split("/")
            expiry_date = datetime.date(int(year), int(month), 1)

            last_day = calendar.monthrange(expiry_date.year, expiry_date.month)[1]
            expiry_date = datetime.date(expiry_date.year, expiry_date.month, last_day)

            if expiry_date < datetime.date.today():
                raise serializers.ValidationError("Card has expired.")
        except ValueError:
            raise serializers.ValidationError("Invalid expiry date.")

        return value

    def validate(self, attrs):
        # Check if a card with the same last 4 digits already exists for this user
        user = self.context["request"].user
        card_number = attrs.get("card_number")

        if card_number:
            last_four = card_number[-4:]
            masked_card_number = f"**** **** **** {last_four}"

            # Check if a card with the same last 4 digits already exists for this user
            if PaymentMethod.objects.filter(
                user=user, type="card", masked_card_number=masked_card_number
            ).exists():
                raise serializers.ValidationError(
                    {
                        "card_number": "A payment method with this card number already exists."
                    }
                )

        return attrs

    def create(self, validated_data):
        card_number = validated_data.pop("card_number")
        cvv = validated_data.pop("cvv")
        payment_method_type = validated_data.pop("payment_method_type")

        last_four = card_number[-4:]
        masked_card_number = f"**** **** **** {last_four}"
        validated_data["masked_card_number"] = masked_card_number

        import hashlib

        cvv_hash = hashlib.sha256(cvv.encode()).hexdigest()

        validated_data["cvv_hash"] = cvv_hash
        validated_data["type"] = "card"
        validated_data["user"] = self.context["request"].user
        validated_data["payment_method_type"] = payment_method_type

        return super().create(validated_data)


@extend_schema_serializer(component_name="MobileMoneyPaymentMethod")
class MobileMoneyPaymentMethodSerializer(serializers.ModelSerializer):
    mobile_number = PhoneNumberField(
        required=True,
        help_text="Mobile number associated with the mobile money account (E.164 format)",
    )
    payment_method_type = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethodType.objects.filter(code__startswith="MOBILE"),
        required=True,
        write_only=True,
        help_text="ID of the mobile money payment method type",
    )

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "default_method",
            "provider",
            "mobile_number",
            "payment_method_type",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "provider": {
                "required": True,
                "help_text": "Mobile money provider (e.g., MTN Mobile Money)",
            },
            "default_method": {
                "help_text": "Whether this is the default payment method"
            },
        }

    def validate(self, attrs):
        # Check if a mobile money payment method with the same provider and mobile number already exists
        user = self.context["request"].user
        provider = attrs.get("provider")
        mobile_number = attrs.get("mobile_number")

        if provider and mobile_number:
            # Convert PhoneNumber object to string if needed
            mobile_number_str = str(mobile_number)
            if hasattr(mobile_number, "as_e164"):
                mobile_number_str = mobile_number.as_e164

            # Check if a mobile money payment method with the same provider and mobile number already exists
            if PaymentMethod.objects.filter(
                user=user,
                type="mobile_money",
                provider=provider,
                mobile_number=mobile_number_str,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "mobile_number": "A payment method with this provider and mobile number already exists."
                    }
                )

        return attrs

    def create(self, validated_data):
        if "mobile_number" in validated_data and hasattr(
            validated_data["mobile_number"], "as_e164"
        ):
            validated_data["mobile_number"] = validated_data["mobile_number"].as_e164

        payment_method_type = validated_data.pop("payment_method_type")
        validated_data["type"] = "mobile_money"
        validated_data["user"] = self.context["request"].user
        validated_data["payment_method_type"] = payment_method_type

        return super().create(validated_data)


@extend_schema_serializer(component_name="Wallet")
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "id",
            "balance",
            "wallet_type",
            "created_at",
            "last_updated",
            "is_active",
        ]
        read_only_fields = ["id", "balance", "created_at", "last_updated"]


@extend_schema_serializer(component_name="CashInTransaction")
class AddFundsTransactionSerializer(serializers.Serializer):
    amount = AppAmountField(required=True, help_text="Amount to add to the wallet")
    payment_method_id = serializers.IntegerField(
        required=True, help_text="ID of the payment method to use"
    )
    wallet_id = serializers.IntegerField(
        required=True, help_text="ID of the wallet to add funds to"
    )
    charged_amount = serializers.FloatField(
        read_only=True, help_text="Total amount charged including transaction fee"
    )
    calculated_fee = serializers.FloatField(
        read_only=True,
        help_text="Transaction fee calculated based on the payment method type",
    )

    def validate_payment_method_id(self, value):
        user = self.context["request"].user
        try:
            payment_method = PaymentMethod.objects.get(pk=value, user=user)
            self.context["payment_method"] = payment_method
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError(
                _("Payment method not found"), code="payment_method_not_found"
            )

    def validate_wallet_id(self, value):
        user = self.context["request"].user
        try:
            wallet = Wallet.objects.get(pk=value, user=user)
            self.context["wallet"] = wallet
            return value
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                _("Wallet not found"), code="wallet_not_found"
            )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Amount must be greater than zero"), code="invalid_amount"
            )
        return value

    def to_representation(self, instance):
        representation = {
            "id": instance.id,
            "reference": instance.reference,
            "amount": instance.amount,
            "status": instance.status,
            "payment_method_id": instance.payment_method_id,
            "wallet_id": instance.wallet_id,
        }

        if instance.calculated_fee is not None:
            representation["calculated_fee"] = instance.calculated_fee

        if instance.charged_amount is not None:
            representation["charged_amount"] = instance.charged_amount

        return representation

    def create(self, validated_data):
        payment_method = self.context["payment_method"]
        wallet = self.context["wallet"]
        user = self.context["request"].user
        amount = validated_data["amount"]

        # Get the payment method type to access the cash-in transaction fee
        payment_method_type = None
        payment_method_type_id = getattr(payment_method, "payment_method_type_id", None)

        if payment_method_type_id:
            try:
                payment_method_type = PaymentMethodType.objects.get(
                    id=payment_method_type_id
                )
            except PaymentMethodType.DoesNotExist:
                pass

        # If payment_method_type is not directly available, try to infer it
        if not payment_method_type:
            if payment_method.type == "card":
                payment_method_type = PaymentMethodType.objects.filter(
                    code__startswith="CARD"
                ).first()
            elif payment_method.type == "mobile_money" and payment_method.provider:
                # Try to match by provider name
                provider_words = payment_method.provider.upper().split()
                for word in provider_words:
                    if len(word) > 2:  # Skip short words like "OF", "THE", etc.
                        matching_type = PaymentMethodType.objects.filter(
                            code__contains=word
                        ).first()
                        if matching_type:
                            payment_method_type = matching_type
                            break

                # If no match by provider words, try a generic mobile money type
                if not payment_method_type:
                    payment_method_type = PaymentMethodType.objects.filter(
                        code__startswith="MOBILE"
                    ).first()

        # Calculate the fee and charged amount if a payment method type with a fee is found
        calculated_fee = None
        charged_amount = amount

        if (
            payment_method_type
            and payment_method_type.cash_in_transaction_fee is not None
        ):
            from app.transactions.utils import compute_inclusive_amount

            calculated_fee, charged_amount = compute_inclusive_amount(
                amount, payment_method_type.cash_in_transaction_fee
            )

        transaction = Transaction.objects.create(
            type=TransactionType.CashIn,
            status=TransactionStatus.INITIATED,
            amount=amount,
            calculated_fee=calculated_fee,
            charged_amount=charged_amount,
            payer_account=user.account if hasattr(user, "account") else None,
            reference=make_transaction_ref(TransactionType.CashIn),
            payment_code=make_payment_code(
                make_transaction_ref(TransactionType.CashIn),
                TransactionType.CashIn,
            ),
            payment_method=payment_method,
            wallet=wallet,
        )

        return transaction


@extend_schema_serializer(component_name="PaymentMethodType")
class PaymentMethodTypeSerializer(serializers.ModelSerializer):
    country_name = serializers.SerializerMethodField()
    country_code = serializers.SerializerMethodField()
    required_fields = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethodType
        fields = [
            "id",
            "name",
            "code",
            "cash_in_transaction_fee",
            "cash_out_transaction_fee",
            "country",
            "country_name",
            "country_code",
            "required_fields",
        ]
        read_only_fields = fields

    def get_country_name(self, obj):
        return obj.country.name if obj.country else None

    def get_country_code(self, obj):
        return obj.country.iso_code if obj.country else None

    def get_required_fields(self, obj):
        if obj.code.startswith("CARD"):
            return {
                "cardholder_name": {
                    "type": "string",
                    "required": True,
                    "help_text": "Name of the cardholder",
                },
                "card_number": {
                    "type": "string",
                    "required": True,
                    "help_text": "Card number (will be masked in responses)",
                },
                "expiry_date": {
                    "type": "string",
                    "required": True,
                    "help_text": "Card expiry date in MM/YYYY format",
                },
                "cvv": {
                    "type": "string",
                    "required": True,
                    "help_text": "Card verification value (3-4 digits)",
                },
                "billing_address": {
                    "type": "string",
                    "required": True,
                    "help_text": "Billing address associated with the card",
                },
            }
        elif obj.code.startswith("MOBILE"):
            return {
                "provider": {
                    "type": "string",
                    "required": True,
                    "help_text": f"Mobile money provider (e.g., {obj.name})",
                },
                "mobile_number": {
                    "type": "string",
                    "required": True,
                    "help_text": "Mobile number associated with the mobile money account (E.164 format)",
                },
            }
        return {}
