
from rest_framework import serializers

from banking.models import Account

class PerformPaymentSerializer(serializers.Serializer):
    from_account = serializers.CharField()
    to_account = serializers.CharField()
    amount = serializers.FloatField()
    notes = serializers.CharField(required=False)

    def validate_amount(self, amount):
        pass

    def validate_from_account(self, from_account_ref):
        from_account = Account.objects.filter(number=from_account_ref).first()

        if not from_account:
            raise serializers.ValidationError("Account not found with this number {}".format(
                from_account_ref))

        return from_account_ref

    def validate_to_account(self, to_account_ref):
        to_account = Account.objects.filter(number=to_account_ref).first()

        if not to_account:
            raise serializers.ValidationError("Account not found with this number {}".format(
                to_account_ref))

        return to_account_ref

    def validate(self, data):
        from_account_ref = data.get('from_account')
        to_account_ref = data.get('to_account')

        accounts = Account.objects.filter(
            number__in=[from_account_ref, to_account_ref])

        if not accounts.exists():
            raise serializers.ValidationError("Accounts not founds")

        accounts.get()





        # check user permissions for both from_account and to_account
        # check if from_account user can perform_payment
        # check if to_account can receive_payment

        return data