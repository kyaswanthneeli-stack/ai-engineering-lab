def divide(a, b):
    if b == 0:
        return 0  # BUG: should raise ZeroDivisionError
    return a / b
