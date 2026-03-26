from decimal import Decimal, ROUND_HALF_UP
from bson import Decimal128
from datetime import datetime, timezone

def to_d128(value) -> Decimal128:
    """Convert numeric/Decimal to Decimal128 for MongoDB storage."""
    if value is None:
        return Decimal128("0.00")
    if isinstance(value, Decimal128):
        return value
    return Decimal128(str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))

def to_decimal(value) -> Decimal:
    """Convert any value to Decimal safely."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(value))

def calculate_wo_financials(subtotal: Decimal, retention_pct: Decimal, cgst_pct: Decimal = Decimal("0"), sgst_pct: Decimal = Decimal("0")):
    """Calculate all financial fields for a Work Order."""
    discount = Decimal("0")
    total_before_tax = subtotal - discount
    cgst_amount = (total_before_tax * cgst_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    sgst_amount = (total_before_tax * sgst_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    grand_total = total_before_tax + cgst_amount + sgst_amount
    retention_amount = (grand_total * retention_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_payable = grand_total - retention_amount
    
    return {
        "subtotal": subtotal,
        "discount": discount,
        "total_before_tax": total_before_tax,
        "cgst": cgst_amount,
        "sgst": sgst_amount,
        "grand_total": grand_total,
        "retention_amount": retention_amount,
        "total_payable": total_payable
    }

def calculate_pc_financials(pc_value: Decimal, retention_pct: Decimal, cgst_pct: Decimal = Decimal("0"), sgst_pct: Decimal = Decimal("0")):
    """Calculate all financial fields for a Payment Certificate."""
    retention_amount = (pc_value * retention_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_payable = pc_value - retention_amount
    cgst_amount = (total_payable * cgst_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    sgst_amount = (total_payable * sgst_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    gst_amount = cgst_amount + sgst_amount
    grand_total = total_payable + gst_amount
    
    return {
        "subtotal": pc_value,
        "retention_amount": retention_amount,
        "total_payable": total_payable,
        "cgst": cgst_amount,
        "sgst": sgst_amount,
        "gst_amount": gst_amount,
        "grand_total": grand_total
    }
