def compute_inclusive_amount(amount, applicable_fee, fee_type=None):
    from decimal import Decimal

    amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
    applicable_fee = (
        Decimal(str(applicable_fee))
        if not isinstance(applicable_fee, Decimal)
        else applicable_fee
    )

    from app.transactions.models import TransactionFee

    if fee_type == TransactionFee.FeePriority.FIXED:
        calculated_fee = applicable_fee
    elif fee_type == TransactionFee.FeePriority.PERCENTAGE:
        calculated_fee = (amount * applicable_fee) / 100
    else:
        if applicable_fee < 100:
            calculated_fee = (amount * applicable_fee) / 100
        else:
            calculated_fee = applicable_fee

    charged_amount = amount + calculated_fee
    return calculated_fee, charged_amount
