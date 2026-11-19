import unittest
from checkout import invoice_total
from pricing import taxable_subtotal

class TestInvoiceRegression(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(invoice_total([0.1, 0.2], 0.1), 0.33)

    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            invoice_total([10, -5], 0.1)

    def test_direct_taxable_subtotal_negative_rejected(self):
        with self.assertRaises(ValueError):
            taxable_subtotal([10, -5])

    def test_direct_taxable_subtotal_rounds_money(self):
        self.assertEqual(taxable_subtotal([0.1, 0.2]), 0.3)
