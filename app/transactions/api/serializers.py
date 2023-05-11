from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from app.transactions.models import Transaction

class P2PTransactionSerializer(serializers.Serializer):
    amount = serializers.FloatField()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(_('Invalid transaction amount'), code='invalid_transaction_amount')
        return value

    def create(self, validated_data) -> Transaction:
        transaction = Transaction.create_P2P_transaction(**validated_data)
        return transaction

    def to_representation(self, instance: Transaction):
        repr = {
            "payment_code": instance.payment_code,
        }

        return repr

