from pricing import taxable_subtotal, round_money


def invoice_total(items, rate):
    if any(item < 0 for item in items):
        raise ValueError('Negative item prices are not allowed')
    subtotal = taxable_subtotal(items)
    tax = round_money(subtotal * rate)
    return round_money(subtotal + tax)
