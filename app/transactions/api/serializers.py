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
            "payer_account",
            "receiver_account",
        )
