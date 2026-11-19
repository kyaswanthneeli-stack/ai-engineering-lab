def round_money(value):
    return round(value, 2)


def taxable_subtotal(items):
    # Validate at the pricing boundary, including direct API callers.
    # Materialize once so a generator is not consumed during validation.
    prices = tuple(items)
    if any(price < 0 for price in prices):
        raise ValueError("Negative item prices are not allowed")
    return round_money(sum(prices))
