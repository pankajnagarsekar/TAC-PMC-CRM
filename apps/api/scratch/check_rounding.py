import sys
import os
from decimal import Decimal, ROUND_HALF_UP

# Add the apps/api directory to sys.path to allow importing 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.shared.domain.financial_engine import FinancialEngine

def check_rounding():
    print(f"Testing FinancialEngine.round (Precision: {FinancialEngine.PRECISION})")
    
    test_values = [
        "1.005", "1.015", "1.025", "1.035", "1.045", "1.055", "1.065", "1.075", "1.085", "1.095",
        "100.005", "100.015", "33.333333", "33.335", "33.345"
    ]
    
    print(f"{'Input':<15} | {'Rounded':<10}")
    print("-" * 30)
    for val in test_values:
        d_val = Decimal(val)
        rounded = FinancialEngine.round(d_val)
        print(f"{val:<15} | {rounded:<10}")

    # Complex calculation test
    pc_value = Decimal("1000")
    retention_pct = Decimal("5")
    cgst_pct = Decimal("9")
    sgst_pct = Decimal("9")
    
    fin = FinancialEngine.calculate_pc_financials(pc_value, retention_pct, cgst_pct, sgst_pct)
    print("\nCalculation Test (1000, 5% Retention, 9% CGST, 9% SGST):")
    for k, v in fin.items():
        print(f"{k:<15}: {v}")

if __name__ == "__main__":
    check_rounding()
