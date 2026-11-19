def round_money(value):
    return round(value, 2)

def taxable_subtotal(items):
    if any(item < 0 for item in items):
        raise ValueError('Negative prices are not allowed')
    return round(sum(items), 2)
