from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

from app.accounts.api import serializers as accounts_serializers
from app.accounts.models import Account, PhoneNumber
from app.core.utils import AppAmountField
from app.transactions.models import Transaction


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
    receiver_account = accounts_serializers.AccountDetailsSerializer()
    payer_account = accounts_serializers.AccountDetailsSerializer()

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


class BasePINSerializer(serializers.Serializer):
    pin = serializers.CharField()


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
    BaseBalanceValidationSerializerMixin, BasePINSerializer
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


class CashOutTransactionSerializer(BasePINSerializer):
    to_phone_number = serializers.CharField()
    amount = AppAmountField()

    def validate_to_phone_number(self, to_phone_number):
        from_account = self.context.get("account")

        to_verified_phone_number = PhoneNumber.objects.phone_number_exists(
            from_account, to_phone_number
        )
        if not to_verified_phone_number:
            raise serializers.ValidationError(
                _("Phone number is not verified"), code="unverified_phone_number"
            )

        self.context["to_verified_phone_number"] = to_verified_phone_number

        return to_phone_number

    # TODO: Refactor compute inclusive amount business logic
    @transaction.atomic
    def create(self, validated_data):
        from_account = self.context["account"]
        to_phone_number = self.context["to_verified_phone_number"]

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

        return transaction

    def to_representation(self, instance):
        return {}
