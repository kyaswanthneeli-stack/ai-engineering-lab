import unittest
from calculator import divide

class TestReproduction(unittest.TestCase):
    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            divide(12, 0)
