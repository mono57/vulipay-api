def compute_inclusive_amount(amount, applicable_fee):
    from decimal import Decimal

    amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
    applicable_fee = (
        Decimal(str(applicable_fee))
        if not isinstance(applicable_fee, Decimal)
        else applicable_fee
    )

    calculated_fee = (amount * applicable_fee) / 100
    charged_amount = amount + calculated_fee
    return calculated_fee, charged_amount
