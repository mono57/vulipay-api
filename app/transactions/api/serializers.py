from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

from app.accounts.api.serializers import (
    AccountDetailsSerializer,
    AccountInfoTransactionHistorySerializer,
    PhoneNumberSerializer,
    PhoneNumberTransactionHistorySerializer,
    PINSerializerMixin,
)
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


class TransactionHistoryListSerializer(serializers.ModelSerializer):
    payer_account = AccountInfoTransactionHistorySerializer()
    receiver_account = AccountInfoTransactionHistorySerializer()
    from_account = AccountInfoTransactionHistorySerializer()
    to_account = AccountInfoTransactionHistorySerializer()
    from_phone_number = PhoneNumberTransactionHistorySerializer()
    to_phone_number = PhoneNumberTransactionHistorySerializer()

    class Meta:
        model = Transaction
        fields = [
            "payer_account",
            "receiver_account",
            "from_account",
            "to_account",
            "from_phone_number",
            "to_phone_number",
            "charged_amount",
            "status",
            "type",
            "created_on",
        ]
