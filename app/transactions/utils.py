def compute_inclusive_amount(amount, applicable_fee, fee_type=None):
    from decimal import Decimal

    amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
    applicable_fee = (
        Decimal(str(applicable_fee))
        if not isinstance(applicable_fee, Decimal)
        else applicable_fee
    )

    # Import TransactionFee inside the function to avoid circular imports
    from app.transactions.models import TransactionFee

    if fee_type == TransactionFee.FeePriority.FIXED:
        # Explicitly set as fixed fee
        calculated_fee = applicable_fee
    elif fee_type == TransactionFee.FeePriority.PERCENTAGE:
        # Explicitly set as percentage fee
        calculated_fee = (amount * applicable_fee) / 100
    else:
        # Auto-detect based on value
        # If fee is less than 100, it's likely a percentage fee (most percentage fees are below 100%)
        # If fee is 100 or more, it's likely a fixed fee
        if applicable_fee < 100:
            calculated_fee = (amount * applicable_fee) / 100
        else:
            calculated_fee = applicable_fee

    charged_amount = amount + calculated_fee
    return calculated_fee, charged_amount
