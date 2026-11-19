import unittest
from calculator import divide

class TestCalculate(unittest.TestCase):
    def test_normal_division(self):
        self.assertEqual(divide(8,2),4)
