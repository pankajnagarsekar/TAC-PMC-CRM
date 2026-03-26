from decimal import Decimal, ROUND_HALF_UP
from bson import Decimal128
from datetime import datetime, timezone
from app.domain.financial_engine import FinancialEngine

def to_d128(value) -> Decimal128:
    """Convert numeric/Decimal to Decimal128 for MongoDB storage."""
    if value is None:
        return Decimal128("0.00")
    if isinstance(value, Decimal128):
        return value
    return Decimal128(str(FinancialEngine.round(value)))

def to_decimal(value) -> Decimal:
    """Convert any value to Decimal safely."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal128):
        return value.to_decimal()
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal("0.00")

def round_half_up(value: Decimal, precision: int = 2) -> Decimal:
    """Explicit Round-Half-Up helper (Delegates to Engine)."""
    return FinancialEngine.round(value)

def calculate_wo_financials(
    subtotal: Decimal, 
    retention_pct: Decimal, 
    discount: Decimal = Decimal("0"), 
    cgst_pct: Decimal = Decimal("9"), 
    sgst_pct: Decimal = Decimal("9")
):
    """
    Fixed CR-11: Delegates to FinancialEngine for authoritative logic.
    Ensures calculations are consistent across the entire domain.
    """
    return FinancialEngine.calculate_wo_financials(
        subtotal=subtotal,
        discount=discount,
        retention_pct=retention_pct,
        cgst_pct=cgst_pct,
        sgst_pct=sgst_pct
    )

def calculate_pc_financials(
    pc_value: Decimal, 
    retention_pct: Decimal, 
    cgst_pct: Decimal = Decimal("9"), 
    sgst_pct: Decimal = Decimal("9")
):
    """
    Fixed CR-11: Delegates to FinancialEngine for authoritative logic.
    """
    return FinancialEngine.calculate_pc_financials(
        pc_value=pc_value,
        retention_pct=retention_pct,
        cgst_pct=cgst_pct,
        sgst_pct=sgst_pct
    )
