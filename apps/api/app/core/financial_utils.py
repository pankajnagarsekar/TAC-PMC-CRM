from decimal import Decimal, ROUND_HALF_UP
from bson import Decimal128
from datetime import datetime, timezone

def to_d128(value) -> Decimal128:
    """Convert numeric/Decimal to Decimal128 for MongoDB storage."""
    if value is None:
        return Decimal128("0.00")
    if isinstance(value, Decimal128):
        return value
    # Ensure 2 decimal places with ROUND_HALF_UP
    return Decimal128(str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))

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
    """Explicit Round-Half-Up helper."""
    quantize_str = "0." + "0" * (precision - 1) + "1" if precision > 0 else "1"
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def calculate_wo_financials(
    subtotal: Decimal, 
    retention_pct: Decimal, 
    discount: Decimal = Decimal("0"), 
    cgst_pct: Decimal = Decimal("9"), 
    sgst_pct: Decimal = Decimal("9")
):
    """Calculate all financial fields for a Work Order."""
    total_before_tax = round_half_up(subtotal - discount)
    cgst_amount = round_half_up(total_before_tax * cgst_pct / 100)
    sgst_amount = round_half_up(total_before_tax * sgst_pct / 100)
    grand_total = round_half_up(total_before_tax + cgst_amount + sgst_amount)
    retention_amount = round_half_up(grand_total * retention_pct / 100)
    actual_payable = round_half_up(grand_total - retention_amount)
    
    return {
        "subtotal": subtotal,
        "discount": discount,
        "total_before_tax": total_before_tax,
        "cgst": cgst_amount,
        "sgst": sgst_amount,
        "grand_total": grand_total,
        "retention_amount": retention_amount,
        "total_payable": grand_total,  # Standard nomenclature in this system
        "actual_payable": actual_payable
    }

def calculate_pc_financials(
    pc_value: Decimal, 
    retention_pct: Decimal, 
    cgst_pct: Decimal = Decimal("9"), 
    sgst_pct: Decimal = Decimal("9")
):
    """Calculate all financial fields for a Payment Certificate."""
    retention_amount = round_half_up(pc_value * retention_pct / 100)
    total_after_retention = round_half_up(pc_value - retention_amount)
    cgst_amount = round_half_up(total_after_retention * cgst_pct / 100)
    sgst_amount = round_half_up(total_after_retention * sgst_pct / 100)
    gst_amount = round_half_up(cgst_amount + sgst_amount)
    grand_total = round_half_up(total_after_retention + gst_amount)
    
    return {
        "subtotal": pc_value,
        "retention_amount": retention_amount,
        "total_after_retention": total_after_retention,
        "cgst": cgst_amount,
        "sgst": sgst_amount,
        "gst_amount": gst_amount,
        "grand_total": grand_total
    }
