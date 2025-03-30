import json
import os
import sys
from decimal import Decimal

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from app.accounts.models import AvailableCountry
from app.transactions.api.serializers import PaymentMethodTypeSerializer
from app.transactions.models import PaymentMethodType, TransactionFee, TransactionType

# Debugging: Print available transaction types
print("Available transaction types:", TransactionType.values)

# Get or create test Country
country, _ = AvailableCountry.objects.get_or_create(
    iso_code="US",
    defaults={
        "name": "United States",
        "dial_code": "+1",
        "phone_number_regex": r"^\+1\d{10}$",
        "currency": "USD",
    },
)

# Define transaction types based on the enum
cash_in_type = TransactionType.CashIn
cash_out_type = TransactionType.CashOut
p2p_type = TransactionType.P2P
merchant_type = TransactionType.MP

print("Using transaction types:", cash_in_type, cash_out_type, p2p_type, merchant_type)

# Get or create a test PaymentMethodType
payment_method_type, created = PaymentMethodType.objects.get_or_create(
    code="TEST_METHOD",
    defaults={
        "name": "Test Payment Method",
        "country": country,
        "allowed_transactions": [
            cash_in_type,
            cash_out_type,
            p2p_type,
        ],
    },
)

print(f"PaymentMethodType created: {created}")
print(f"PaymentMethodType ID: {payment_method_type.id}")
print(
    f"PaymentMethodType allowed_transactions: {payment_method_type.allowed_transactions}"
)

# Update the payment method type with allowed transactions
payment_method_type.allowed_transactions = [cash_in_type, cash_out_type, p2p_type]
payment_method_type.save()

print(
    f"PaymentMethodType after update - allowed_transactions: {payment_method_type.allowed_transactions}"
)

if (
    created
    or not TransactionFee.objects.filter(
        payment_method_type=payment_method_type
    ).exists()
):
    print("Creating transaction fees...")
    # Create transaction fees for testing
    # Cash in fee (fixed)
    TransactionFee.objects.create(
        payment_method_type=payment_method_type,
        transaction_type=cash_in_type,
        country=country,
        fixed_fee=2.50,
        percentage_fee=None,
        fee_priority=TransactionFee.FeePriority.FIXED,
    )

    # Cash out fee (percentage)
    TransactionFee.objects.create(
        payment_method_type=payment_method_type,
        transaction_type=cash_out_type,
        country=country,
        fixed_fee=None,
        percentage_fee=1.5,
        fee_priority=TransactionFee.FeePriority.PERCENTAGE,
    )

    # P2P fee (fixed)
    TransactionFee.objects.create(
        payment_method_type=payment_method_type,
        transaction_type=p2p_type,
        country=country,
        fixed_fee=1.00,
        percentage_fee=None,
        fee_priority=TransactionFee.FeePriority.FIXED,
    )

    # Merchant payment fee (percentage)
    TransactionFee.objects.create(
        payment_method_type=payment_method_type,
        transaction_type=merchant_type,
        country=country,
        fixed_fee=None,
        percentage_fee=2.0,
        fee_priority=TransactionFee.FeePriority.PERCENTAGE,
    )

# Serialize the PaymentMethodType instance
serializer = PaymentMethodTypeSerializer(payment_method_type)
serialized_data = serializer.data

# Pretty print the serialized data
print("\n-- PaymentMethodType Serialized Data --")
print(json.dumps(serialized_data, indent=2))

# Print transaction fees specifically
print("\n-- Transaction Fees --")
print(json.dumps(serialized_data.get("transaction_fees", {}), indent=2))

# Print allowed transactions specifically
print("\n-- Allowed Transactions --")
print(json.dumps(serialized_data.get("allowed_transactions", []), indent=2))
