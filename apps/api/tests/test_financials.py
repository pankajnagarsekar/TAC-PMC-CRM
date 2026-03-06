import unittest
from decimal import Decimal
from financial_service import FinancialRecalculationService

class TestFinancialRounding(unittest.TestCase):
    def test_round_half_up(self):
        # 0.005 -> 0.01 (Rounding up)
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("0.005")), Decimal("0.01"))
        
        # 0.004 -> 0.00 (Rounding down)
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("0.004")), Decimal("0.00"))
        
        # 1.255 -> 1.26
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("1.255")), Decimal("1.26"))
        
        # 1.254 -> 1.25
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("1.254")), Decimal("1.25"))
        
        # Exact values
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("1.25")), Decimal("1.25"))
        
    def test_precision(self):
        # 0.0055 -> 0.006 with precision 3
        self.assertEqual(FinancialRecalculationService.round_half_up(Decimal("0.0055"), precision=3), Decimal("0.006"))

if __name__ == "__main__":
    unittest.main()
