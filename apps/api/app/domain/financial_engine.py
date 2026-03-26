from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
import hashlib
import json

class FinancialEngine:
    """
    Sovereign Domain Logic for all calculations (Point 1, 81, 85, 86).
    Enforces ROUND_HALF_UP and prevents data drift via logic versioning.
    """
    DOMAIN_LOGIC_VERSION: int = 1
    PRECISION: Decimal = Decimal("0.01")

    @classmethod
    def round(cls, value: Any) -> Decimal:
        """Standardized Round-Half-Up (Point 1)"""
        if value is None: return Decimal("0.00")
        return Decimal(str(value)).quantize(cls.PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_wo_financials(cls, subtotal: Decimal, discount: Decimal, retention_pct: Decimal, cgst_pct: Decimal, sgst_pct: Decimal) -> Dict[str, Any]:
        """Core logic for Work Orders (Point 1, 86)"""
        subtotal = cls.round(subtotal)
        discount = cls.round(discount)
        
        total_before_tax = cls.round(subtotal - discount)
        if total_before_tax < 0:
            raise ValueError("DOMAIN_ERROR: Subtotal cannot be negative after discount.")

        cgst_amount = cls.round(total_before_tax * cgst_pct / 100)
        sgst_amount = cls.round(total_before_tax * sgst_pct / 100)
        grand_total = cls.round(total_before_tax + cgst_amount + sgst_amount)
        
        retention_amount = cls.round(grand_total * retention_pct / 100)
        actual_payable = cls.round(grand_total - retention_amount)

        return {
            "subtotal": subtotal,
            "discount": discount,
            "total_before_tax": total_before_tax,
            "cgst": cgst_amount,
            "sgst": sgst_amount,
            "gst_amount": cls.round(cgst_amount + sgst_amount),
            "grand_total": grand_total,
            "retention_amount": retention_amount,
            "actual_payable": actual_payable,
            "logic_version": cls.DOMAIN_LOGIC_VERSION
        }

    @classmethod
    def calculate_pc_financials(cls, pc_value: Decimal, retention_pct: Decimal, cgst_pct: Decimal, sgst_pct: Decimal) -> Dict[str, Any]:
        """Core logic for Payment Certificates (Point 81, 85)"""
        pc_value = cls.round(pc_value)
        retention_amount = cls.round(pc_value * retention_pct / 100)
        total_after_retention = cls.round(pc_value - retention_amount)
        
        cgst_amount = cls.round(total_after_retention * cgst_pct / 100)
        sgst_amount = cls.round(total_after_retention * sgst_pct / 100)
        gst_amount = cls.round(cgst_amount + sgst_amount)
        grand_total = cls.round(total_after_retention + gst_amount)

        return {
            "subtotal": pc_value,
            "retention_amount": retention_amount,
            "total_after_retention": total_after_retention,
            "cgst": cgst_amount,
            "sgst": sgst_amount,
            "gst_amount": gst_amount,
            "grand_total": grand_total,
            "logic_version": cls.DOMAIN_LOGIC_VERSION
        }

    @classmethod
    def generate_fingerprint(cls, context: Dict[str, Any]) -> str:
        """Create a deterministic hash to prevent double-spending (Point 81)"""
        # Sort keys to ensure consistent hashing
        serial_context = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(serial_context.encode()).hexdigest()

    @classmethod
    def verify_integrity(cls, data: Dict[str, Any], expected_checksum: str) -> bool:
        """Verify data hasn't been corrupted in DB (Point 108)"""
        # Typically called by Consistency Guardian jobs
        actual = cls.generate_fingerprint({k: v for k, v in data.items() if k != "checksum"})
        return actual == expected_checksum
