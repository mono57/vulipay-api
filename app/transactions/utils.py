def compute_inclusive_amount(amount, applicable_fee):
    calculated_fee = (amount * applicable_fee) / 100
    charged_amount = amount + calculated_fee
    return calculated_fee, charged_amount
