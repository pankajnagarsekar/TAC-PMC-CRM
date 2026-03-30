import os
import sys
import unittest

# Add app to path for testing environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decimal import Decimal  # noqa: E402
from app.modules.financial.domain.financial_engine import FinancialEngine  # noqa: E402


class TestFinancialRounding(unittest.TestCase):
    def test_round_half_up(self):
        # 0.005 -> 0.01 (Rounding up)
        self.assertEqual(FinancialEngine.round(Decimal("0.005")), Decimal("0.01"))

        # 0.004 -> 0.00 (Rounding down)
        self.assertEqual(FinancialEngine.round(Decimal("0.004")), Decimal("0.00"))

        # 1.255 -> 1.26
        self.assertEqual(FinancialEngine.round(Decimal("1.255")), Decimal("1.26"))

        # 1.254 -> 1.25
        self.assertEqual(FinancialEngine.round(Decimal("1.254")), Decimal("1.25"))

        # Exact values
        self.assertEqual(FinancialEngine.round(Decimal("1.25")), Decimal("1.25"))

    def test_precision(self):
        # 0.0055 -> 0.006 with precision 3
        self.assertEqual(
            FinancialEngine.round(Decimal("0.0055"), precision=3), Decimal("0.006")
        )


if __name__ == "__main__":
    unittest.main()
