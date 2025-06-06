import calendar
import datetime
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import exceptions, serializers

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
from app.transactions.utils import compute_inclusive_amount, process_fee_dict

User = get_user_model()


@extend_schema_serializer(
    component_name="PaymentMethod",
    examples=[
        OpenApiExample(
            name="Example Payment Method",
            value={
                "id": 1,
                "type": "card",
                "default_method": True,
                "cardholder_name": "John Doe",
                "masked_card_number": "**** **** **** 1234",
                "expiry_date": "12/2025",
                "payment_method_type_name": "Visa Card",
                "transactions_fees": [
                    {
                        "transaction_type": "CI",
                        "transaction_type_display": "Cash In",
                        "fee": 100,
                        "fee_type": "fixed",
                    },
                    {
                        "transaction_type": "CO",
                        "transaction_type_display": "Cash Out",
                        "fee": 2.5,
                        "fee_type": "percentage",
                    },
                ],
                "image": "https://example.com/logo.png",
                "description": "Card ending with 1234",
            },
            summary="Example of a payment method",
        )
    ],
)
class PaymentMethodSerializer(serializers.ModelSerializer):
    payment_method_type = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethodType.objects.all(),
        required=False,
        write_only=True,
        help_text="ID of the payment method type",
    )
    transactions_fees = serializers.SerializerMethodField(
        help_text="List of transaction fees for different transaction types"
    )
    payment_method_type_name = serializers.SerializerMethodField(
        help_text="Name of the payment method type"
    )
    description = serializers.SerializerMethodField(
        help_text="Description of the payment method type"
    )
    image = serializers.ImageField(
        source="payment_method_type.logo",
        read_only=True,
        help_text="Logo image for the payment method type",
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
            "transactions_fees",
            "image",
            "description",
        ]
        read_only_fields = [
            "id",
            "payment_method_type_name",
            "transactions_fees",
            "image",
            "description",
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

    def get_transactions_fees(self, obj):
        payment_method_type = self.get_payment_method_type(obj)
        if not payment_method_type:
            return None

        try:
            fee_objs = TransactionFee.objects.filter(
                payment_method_type=payment_method_type,
                country=obj.user.country,
            ).select_related("country")

            # Filter by transaction_type if it's in the context
            transaction_type = self.context.get("transaction_type")
            if transaction_type:
                fee_objs = fee_objs.filter(transaction_type=transaction_type)

            if not fee_objs:
                return None

            transaction_fees = []
            for fee_obj in fee_objs:
                fee_type = None
                fee_value = None

                if fee_obj.fee_priority == TransactionFee.FeePriority.FIXED:
                    fee_value = fee_obj.fixed_fee
                    fee_type = "fixed"
                elif fee_obj.fee_priority == TransactionFee.FeePriority.PERCENTAGE:
                    fee_value = fee_obj.percentage_fee
                    fee_type = "percentage"

                if fee_value is not None:
                    fee_data = {
                        "transaction_type": fee_obj.transaction_type,
                        "transaction_type_display": dict(TransactionType.choices).get(
                            fee_obj.transaction_type
                        ),
                        "fee": fee_value,
                        "fee_type": fee_type,
                    }
                    transaction_fees.append(fee_data)

            return transaction_fees if transaction_fees else None
        except Exception:
            pass

        return None

    def get_payment_method_type_name(self, obj):
        payment_method_type = self.get_payment_method_type(obj)
        return payment_method_type.name if payment_method_type else None

    def get_description(self, obj):
        if obj.type == "card":
            # Use the last 4 digits from masked_card_number
            if obj.masked_card_number and len(obj.masked_card_number) >= 4:
                last_four = obj.masked_card_number[-4:]
                return f"Card ending with {last_four}"
            return "Card"
        elif obj.type == "mobile_money":
            if obj.provider:
                return f"Mobile Money ending with {obj.mobile_number[-4:]}"
            return "Mobile Money"
        elif obj.type == "wallet":
            return "Wallet"
        return None

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
            "currency",
            "created_on",
            "last_updated",
            "is_active",
        ]
        read_only_fields = ["id", "balance", "created_on", "last_updated"]


@extend_schema_serializer(component_name="Transaction")
class TransactionSerializer(serializers.ModelSerializer):
    from_wallet_id = serializers.IntegerField(
        source="from_wallet.id", read_only=True, allow_null=True
    )
    to_wallet_id = serializers.IntegerField(
        source="to_wallet.id", read_only=True, allow_null=True
    )
    payment_method_id = serializers.IntegerField(
        source="payment_method.id", read_only=True, allow_null=True
    )
    transaction_date = serializers.DateTimeField(source="created_on", read_only=True)
    signed_amount = serializers.SerializerMethodField(
        help_text=_("Amount with sign indicating debit or credit")
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference",
            "amount",
            "signed_amount",
            "charged_amount",
            "calculated_fee",
            "status",
            "type",
            "notes",
            "from_wallet_id",
            "to_wallet_id",
            "payment_method_id",
            "transaction_date",
        ]
        read_only_fields = fields

    def get_signed_amount(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
            if obj.to_wallet and obj.to_wallet.user_id == user.id:
                return obj.amount
            elif obj.from_wallet and obj.from_wallet.user_id == user.id:
                return -obj.amount

        if obj.type == "CI":
            return obj.amount
        elif obj.type == "CO":
            return -obj.amount

        return obj.amount


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
            "wallet_id": instance.to_wallet_id,
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

        payment_method_type = None
        payment_method_type_id = getattr(payment_method, "payment_method_type_id", None)

        if payment_method_type_id:
            try:
                payment_method_type = PaymentMethodType.objects.get(
                    id=payment_method_type_id
                )
            except PaymentMethodType.DoesNotExist:
                pass

        if not payment_method_type:
            if payment_method.type == "card":
                payment_method_type = PaymentMethodType.objects.filter(
                    code__startswith="CARD"
                ).first()
            elif payment_method.type == "mobile_money" and payment_method.provider:
                provider_words = payment_method.provider.upper().split()
                for word in provider_words:
                    if len(word) > 2:
                        matching_type = PaymentMethodType.objects.filter(
                            code__contains=word
                        ).first()
                        if matching_type:
                            payment_method_type = matching_type
                            break

                if not payment_method_type:
                    payment_method_type = PaymentMethodType.objects.filter(
                        code__startswith="MOBILE"
                    ).first()

        if payment_method_type and payment_method_type.allowed_transactions:
            transaction_type = TransactionType.CashIn
            if transaction_type not in payment_method_type.allowed_transactions:
                raise serializers.ValidationError(
                    _(
                        f"Transaction type '{transaction_type}' is not allowed for this payment method type."
                    )
                )

        calculated_fee = None
        charged_amount = amount

        if payment_method_type:
            country = user.country if hasattr(user, "country") else None
            fee_record = TransactionFee.objects.filter(
                country=country,
                transaction_type=TransactionType.CashIn,
                payment_method_type=payment_method_type,
            ).first()

            if fee_record:
                if fee_record.fee_priority == TransactionFee.FeePriority.FIXED:
                    calculated_fee = fee_record.fixed_fee
                    charged_amount = amount + calculated_fee
                elif fee_record.fee_priority == TransactionFee.FeePriority.PERCENTAGE:
                    calculated_fee = (amount * fee_record.percentage_fee) / 100
                    charged_amount = amount + calculated_fee

        transaction = Transaction.create_transaction(
            transaction_type=TransactionType.CashIn,
            amount=amount,
            target_wallet=wallet,
            payment_method=payment_method,
            status=TransactionStatus.INITIATED,
            notes=f"Cash in via {payment_method.type}",
            calculated_fee=calculated_fee,
            charged_amount=charged_amount,
        )

        if calculated_fee is not None and charged_amount is not None:
            transaction.calculated_fee = calculated_fee
            transaction.charged_amount = charged_amount
            transaction.save()

        return transaction


@extend_schema_serializer(
    component_name="PaymentMethodType",
    examples=[
        OpenApiExample(
            name="Example PaymentMethodType",
            value={
                "id": 1,
                "name": "Visa Card",
                "code": "CARD_VISA",
                "country": 1,
                "country_name": "Cameroon",
                "country_code": "CM",
                "transactions_fees": [
                    {
                        "transaction_type": "CI",
                        "transaction_type_display": "Cash In",
                        "fee": 100,
                        "fee_type": "fixed",
                    },
                    {
                        "transaction_type": "CO",
                        "transaction_type_display": "Cash Out",
                        "fee": 2.5,
                        "fee_type": "percentage",
                    },
                ],
                "required_fields": {
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
                    # Additional fields omitted for brevity
                },
                "image": "https://example.com/logo.png",
            },
            summary="Example of a payment method type",
        )
    ],
)
class PaymentMethodTypeSerializer(serializers.ModelSerializer):
    country_name = serializers.SerializerMethodField()
    country_code = serializers.SerializerMethodField()
    required_fields = serializers.SerializerMethodField()
    transactions_fees = serializers.SerializerMethodField(
        help_text="List of transaction fees for different transaction types"
    )
    image = serializers.ImageField(
        source="logo",
        read_only=True,
        help_text="Logo image for the payment method type",
    )

    class Meta:
        model = PaymentMethodType
        fields = [
            "id",
            "name",
            "code",
            "country",
            "country_name",
            "country_code",
            "required_fields",
            "transactions_fees",
            "image",
        ]
        read_only_fields = fields

    def get_country_name(self, obj):
        return obj.country.name if obj.country else None

    def get_country_code(self, obj):
        return obj.country.iso_code if obj.country else None

    def get_transactions_fees(self, obj):
        """Return a list of transaction fees for all transaction types."""
        if not obj.country:
            return None

        # Get all transaction fees in a single query for optimization
        fee_records = TransactionFee.objects.filter(
            country=obj.country,
            payment_method_type=obj,
        ).select_related("country")

        # Filter by transaction_type if it's in the context
        transaction_type = self.context.get("transaction_type")
        if transaction_type:
            fee_records = fee_records.filter(transaction_type=transaction_type)

        if not fee_records:
            return None

        transaction_fees = []
        for fee_record in fee_records:
            fee_value = None
            fee_type = None

            if fee_record.fee_priority == TransactionFee.FeePriority.FIXED:
                fee_value = fee_record.fixed_fee
                fee_type = "fixed"
            elif fee_record.fee_priority == TransactionFee.FeePriority.PERCENTAGE:
                fee_value = fee_record.percentage_fee
                fee_type = "percentage"

            if fee_value is not None:
                fee_data = {
                    "transaction_type": fee_record.transaction_type,
                    "transaction_type_display": dict(TransactionType.choices).get(
                        fee_record.transaction_type
                    ),
                    "fee": fee_value,
                    "fee_type": fee_type,
                }
                transaction_fees.append(fee_data)

        return transaction_fees if transaction_fees else None

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


class ReceiveFundsPaymentCodeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text=_("Optional amount to include in the payment code"),
    )

    def to_representation(self, instance):
        return super().to_representation(instance)


class UserDataDecryptionSerializer(serializers.Serializer):
    encrypted_data = serializers.CharField(
        required=True,
        help_text=_("Encrypted data string to be decrypted"),
    )

    def to_representation(self, instance):
        return super().to_representation(instance)


class ProcessTransactionSerializer(serializers.Serializer):
    amount = AppAmountField(required=True, help_text=_("Amount to be transferred"))
    transaction_type = serializers.ChoiceField(
        choices=TransactionType.choices,
        required=True,
        help_text=_("Type of transaction to process"),
    )
    target_wallet_id = serializers.IntegerField(
        required=True, help_text=_("ID of the recipient's wallet")
    )
    payment_method_id = serializers.IntegerField(
        required=True, help_text=_("ID of the payment method to use")
    )
    payment_method_type_id = serializers.IntegerField(
        required=True, help_text=_("ID of the payment method type to use")
    )
    payment_method_type_code = serializers.CharField(
        required=True, help_text=_("Type of the payment method")
    )
    currency = serializers.CharField(
        required=True,
        help_text=_("Currency code of the transaction (e.g., USD, EUR, XAF)"),
    )
    full_name = serializers.CharField(
        required=False, help_text=_("Name of the recipient")
    )

    def validate_currency(self, value):
        user = self.context["request"].user
        user_currency = user.country.currency

        if value != user_currency:
            raise serializers.ValidationError(
                _(
                    "Currency mismatch. Expected: {expected}, provided: {provided}"
                ).format(expected=user_currency, provided=value)
            )
        return value

    def validate_target_wallet_id(self, value):
        try:
            target_wallet = Wallet.objects.get(id=value)
            self.context["target_wallet"] = target_wallet
            return value
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(_("Target wallet does not exist"))

    def validate(self, attrs):
        user = self.context["request"].user

        if attrs.get("payment_method_type_code") != "WalletToWallet":
            raise serializers.ValidationError({"detail": _("Invalid payment method")})

        source_wallet = Wallet.objects.get_wallet(attrs.get("payment_method_id"), user)
        if not source_wallet:
            raise serializers.ValidationError(
                {"detail": _("Source wallet not found for the user")}
            )

        fee = TransactionFee.objects.get_applicable_fee(
            country=user.country,
            transaction_type=attrs.get("transaction_type"),
            payment_method_type_id=attrs.get("payment_method_type_id"),
        )
        if not fee:
            raise serializers.ValidationError(
                {"detail": _("Transaction fee not found")}
            )
        calculated_fee, charged_amount = process_fee_dict(
            amount=attrs.get("amount"),
            fee_dict={
                "fee_value": fee,
                "fee_type": TransactionFee.FeePriority.PERCENTAGE,
            },
        )

        if source_wallet.balance < charged_amount:
            raise serializers.ValidationError(
                {"detail": _("Insufficient funds in your wallet")}
            )

        if not PaymentMethodType.is_transaction_allowed(
            transaction_type=attrs.get("transaction_type"),
            payment_method_type_id=attrs.get("payment_method_type_id"),
        ):
            raise serializers.ValidationError(
                {
                    "detail": _(
                        f"Payment method not allowed for this transaction type {attrs.get('transaction_type')}"
                    )
                }
            )

        attrs["charged_amount"] = charged_amount
        attrs["calculated_fee"] = calculated_fee
        attrs["source_wallet"] = source_wallet
        attrs["target_wallet"] = self.context["target_wallet"]

        return attrs
