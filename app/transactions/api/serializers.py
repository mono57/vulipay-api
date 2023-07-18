from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

from app.accounts.api import serializers as accounts_serializers
from app.accounts.models import Account
from app.transactions.models import Transaction


class BaseTransactionSerializer(serializers.Serializer):
    amount = serializers.FloatField()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Invalid transaction amount"), code="invalid_transaction_amount"
            )
        return value


class P2PTransactionSerializer(BaseTransactionSerializer):
    def create(self, validated_data) -> Transaction:
        transaction = Transaction.create_P2P_transaction(**validated_data)
        return transaction

    def to_representation(self, instance: Transaction):
        repr = {
            "payment_code": instance.payment_code,
        }

        return repr


class MPTransactionSerializer(BaseTransactionSerializer):
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
        payer_account: Account = validated_data.get("payer_account")
        charge_amount = instance.get_inclusive_amount(payer_account.country)
        code = payer_account.check_balance(charge_amount)

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
        validated_data.setdefault("payer_account", instance.payer_account)

        instance: Transaction = super().update(instance, validated_data)

        instance.perform_payment()

        return instance


class TransactionPairingSerializer(
    BaseBalanceValidationSerializerMixin, serializers.Serializer
):
    def update(self, instance: Transaction, validated_data):
        instance = super().update(instance, validated_data)

        instance.pair(validated_data.get("payer_account"))

        return instance
