import unittest
from checkout import invoice_total

class TestExistingInvoice(unittest.TestCase):
    def test_whole_price_order(self):
        self.assertEqual(invoice_total([10, 5], 0.1), 16.5)
