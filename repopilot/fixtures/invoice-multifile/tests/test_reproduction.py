import unittest

from checkout import invoice_total
from pricing import taxable_subtotal


class TestInvoiceRegression(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(invoice_total([0.1, 0.2], 0.1), 0.33)

    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            invoice_total([10, -5], 0.1)

    def test_direct_subtotal_rejects_negative_price(self):
        with self.assertRaises(ValueError):
            taxable_subtotal([10, -5])

    def test_direct_subtotal_rounds_money(self):
        self.assertEqual(taxable_subtotal([0.1, 0.2]), 0.3)

    def test_iterator_prices_validated_and_totalled_once(self):
        self.assertEqual(invoice_total(iter([10, 5]), 0.1), 16.5)
        with self.assertRaises(ValueError):
            invoice_total(iter([10, -5]), 0.1)

    def test_original_valid_prices_unchanged(self):
        self.assertEqual(invoice_total([10, 5], 0.1), 16.5)
