import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List

from bson import Decimal128

from .exceptions import FinancialIntegrityError


class FinancialEngine:
    """
    Sovereign Domain Logic for all calculations.
    Enforces ROUND_HALF_UP and prevents data drift via logic versioning.
    This is the Single Source of Truth for the entire ecosystem.
    """

    DOMAIN_LOGIC_VERSION: int = 1
    PRECISION: Decimal = Decimal("0.01")

    @staticmethod
    def to_d128(value: Any) -> Decimal128:
        """Sovereign MongoDB conversion (Point 75)."""
        if value is None:
            return Decimal128("0.00")
        if isinstance(value, Decimal128):
            return value
        return Decimal128(str(FinancialEngine.round(value)))

    @staticmethod
    def to_decimal(value: Any) -> Decimal:
        """Sovereign Decimal conversion."""
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal128):
            return value.to_decimal()
        try:
            from decimal import InvalidOperation
            return Decimal(str(value))
        except (ValueError, TypeError, InvalidOperation):
            from .exceptions import ValidationError
            raise ValidationError(f"Invalid numeric value: {value}")

    @classmethod
    def round(cls, value: Any, precision: Any = None) -> Decimal:
        """Standardized Round-Half-Up with support for int or Decimal precision."""
        if value is None:
            return Decimal("0.00")
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        if precision is None:
            target_precision = cls.PRECISION
        elif isinstance(precision, int):
            # Convert integer (e.g., 3) to Decimal scale (e.g., 0.001)
            target_precision = Decimal(10) ** -precision
        else:
            target_precision = precision

        rounded = value.quantize(target_precision, rounding=ROUND_HALF_UP)
        # BUG-025: Fix negative zero display artefact
        if rounded == Decimal("0") or rounded == Decimal("-0"):
            return Decimal("0.00")
        return rounded

    @classmethod
    def calculate_tax(cls, amount: Decimal, tax_pct: Decimal) -> Decimal:
        """Calculate tax portion of a value."""
        return cls.round(amount * (tax_pct / Decimal("100")))

    @classmethod
    def calculate_retention(cls, amount: Decimal, retention_pct: Decimal) -> Decimal:
        """Calculate retention portion."""
        return cls.round(amount * (retention_pct / Decimal("100")))

    @classmethod
    def calculate_line_items(cls, line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process line items and return processed list + subtotal."""
        processed = []
        subtotal = Decimal("0.00")
        for item in line_items:
            qty = cls.round(item.get("qty", 0))
            rate = cls.round(item.get("rate", 0))
            total = cls.round(qty * rate)
            subtotal += total
            item_copy = item.copy()
            item_copy["qty"] = qty
            item_copy["rate"] = rate
            item_copy["total"] = total
            processed.append(item_copy)
        return {"items": processed, "subtotal": subtotal}

    @classmethod
    def calculate_wo_financials(
        cls,
        subtotal: Decimal,
        discount_value: Decimal,
        discount_type: str,  # "percentage" or "value"
        retention_pct: Decimal,
        cgst_pct: Decimal,
        sgst_pct: Decimal,
    ) -> Dict[str, Any]:
        """Core logic for Work Orders. (Strict CR-11/75 alignment)."""
        subtotal = cls.round(subtotal)
        discount_value = cls.round(discount_value)

        if discount_type == "percentage":
            calculated_discount = cls.round(subtotal * (discount_value / Decimal("100")))
        else:
            calculated_discount = discount_value

        total_before_tax = cls.round(subtotal - calculated_discount)
        if total_before_tax < 0:
            raise FinancialIntegrityError("Subtotal cannot be negative after discount.")

        cgst_amount = cls.calculate_tax(total_before_tax, cgst_pct)
        sgst_amount = cls.calculate_tax(total_before_tax, sgst_pct)
        gst_amount = cls.round(cgst_amount + sgst_amount)

        retention_amount = cls.calculate_retention(total_before_tax, retention_pct)
        grand_total = cls.round(total_before_tax + gst_amount)
        actual_payable = cls.round(grand_total - retention_amount)

        if grand_total < 0:
            raise FinancialIntegrityError("Grand total cannot be negative.")

        if actual_payable < 0:
            # This can happen if retention > grand_total (unlikely but possible with weird pct)
            actual_payable = Decimal("0.00")

        return {
            "subtotal": subtotal,
            "discount": calculated_discount,
            "discount_value": discount_value,
            "discount_type": discount_type,
            "after_discount": total_before_tax,  # Alias for total_before_tax
            "total_before_tax": total_before_tax,
            "cgst": cgst_amount,
            "sgst": sgst_amount,
            "gst_amount": gst_amount,
            "grand_total": grand_total,
            "retention_amount": retention_amount,
            "total_payable": grand_total,  # §3.3: total_payable = grand_total (Fixed BUG-005)
            "actual_payable": actual_payable,
            "logic_version": cls.DOMAIN_LOGIC_VERSION,
        }

    @classmethod
    def calculate_pc_financials(
        cls,
        pc_value: Decimal,
        retention_pct: Decimal,
        cgst_pct: Decimal,
        sgst_pct: Decimal,
    ) -> Dict[str, Any]:
        """
        Sovereign PC Logic (Corrected for statutory compliance).
        Formula: Grand Total = (Subtotal + CGST + SGST)
        Retention is a payment deduction from the Grand Total.
        GST is calculated on the FULL Gross Subtotal (BUG-003).
        """
        pc_value = cls.round(pc_value)
        retention_amount = cls.calculate_retention(pc_value, retention_pct)
        
        # BUG-003 FIX: Calculate GST on FULL value, not post-retention
        cgst_amount = cls.calculate_tax(pc_value, cgst_pct)
        sgst_amount = cls.calculate_tax(pc_value, sgst_pct)
        gst_amount = cls.round(cgst_amount + sgst_amount)

        # grand_total = Gross + GST
        grand_total = cls.round(pc_value + gst_amount)
        # actual_payable = (Gross + GST) - Retention
        actual_payable = cls.round(grand_total - retention_amount)

        return {
            "subtotal": pc_value,
            "cgst": cgst_amount,
            "sgst": sgst_amount,
            "gst_amount": gst_amount,
            "grand_total": grand_total,
            "retention_amount": retention_amount,
            "actual_payable": actual_payable,
            "net_payable": actual_payable,  # Authoritative name for Net Payable (BUG-001)
            "logic_version": cls.DOMAIN_LOGIC_VERSION,
        }

    @classmethod
    def generate_fingerprint(cls, context: Dict[str, Any]) -> str:
        """Create a deterministic hash to prevent double-spending."""
        # Sort keys to ensure consistent hashing
        serial_context = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(serial_context.encode()).hexdigest()

    @classmethod
    def verify_integrity(cls, data: Dict[str, Any], expected_checksum: str) -> bool:
        """Verify data hasn't been corrupted in DB."""
        actual = cls.generate_fingerprint(
            {k: v for k, v in data.items() if k != "checksum"}
        )
        return actual == expected_checksum
