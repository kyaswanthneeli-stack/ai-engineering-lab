from pricing import taxable_subtotal, round_money


def invoice_total(items, rate):
    subtotal = taxable_subtotal(items)
    tax = round_money(subtotal * rate)
    return round_money(subtotal + tax)
