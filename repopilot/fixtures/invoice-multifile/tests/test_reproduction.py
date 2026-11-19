import unittest
from checkout import invoice_total

class TestInvoiceRegression(unittest.TestCase):
    def test_rounding(self):
        self.assertEqual(invoice_total([0.1, 0.2], 0.1), 0.33)

    def test_negative_price_rejected(self):
        with self.assertRaises(ValueError):
            invoice_total([10, -5], 0.1)
