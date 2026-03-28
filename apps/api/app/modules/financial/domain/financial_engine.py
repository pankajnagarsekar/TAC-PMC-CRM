from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

class FinancialEngine:
    """
    Sovereign Engine for complex spreadsheet-like calculations (Point 11).
    Enforces cross-functional consistency for TAX, DISCOUNT, and RETENTION.
    """
    
    @staticmethod
    def round(value: Decimal, precision: int = 2) -> Decimal:
        """Sovereign rounding logic for all financial data (Point 11, 75)."""
        if not isinstance(value, Decimal):
            value = Decimal(str(value or 0))
        return value.quantize(Decimal(f"1.{'0'*precision}"), rounding=ROUND_HALF_UP)

    @staticmethod
    def generate_fingerprint(context: Dict[str, Any]) -> str:
        """Create a deterministic hash of the business context to prevent logical duplicates (Point 81)."""
        import hashlib
        import json
        # Sort keys for determinism, use str default for non-serializable fields
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_str.encode()).hexdigest()

    @classmethod
    def calculate_tax(cls, amount: Decimal, tax_pct: Decimal) -> Decimal:
        """Calculate tax part of a value."""
        return cls.round(amount * (tax_pct / Decimal("100")))

    @classmethod
    def calculate_retention(cls, amount: Decimal, retention_pct: Decimal) -> Decimal:
        """Calculate retention part."""
        return cls.round(amount * (retention_pct / Decimal("100")))

    @classmethod
    def calculate_wo_financials(
        cls, 
        subtotal: Decimal, 
        retention_pct: Decimal, 
        discount: Decimal = Decimal("0"),
        cgst_pct: Decimal = Decimal("9"),
        sgst_pct: Decimal = Decimal("9")
    ) -> Dict[str, Any]:
        """
        Fixed CR-11: Authoritative WorkOrder calculation logic.
        Matches exactly with spreadsheet formulas.
        """
        after_discount = subtotal - discount
        cgst = cls.calculate_tax(after_discount, cgst_pct)
        sgst = cls.calculate_tax(after_discount, sgst_pct)
        total_value = after_discount + cgst + sgst
        retention_value = cls.calculate_retention(after_discount, retention_pct)
        
        return {
            "subtotal": cls.round(subtotal),
            "discount": cls.round(discount),
            "after_discount": cls.round(after_discount),
            "cgst": cgst,
            "sgst": sgst,
            "total_value": total_value,
            "retention_value": retention_value,
            "net_payable": total_value - retention_value
        }

    @classmethod
    def calculate_pc_financials(
        cls, 
        pc_value: Decimal, 
        retention_pct: Decimal,
        cgst_pct: Decimal = Decimal("9"),
        sgst_pct: Decimal = Decimal("9")
    ) -> Dict[str, Any]:
        """Authoritative Payment Certificate calculation logic."""
        cgst = cls.calculate_tax(pc_value, cgst_pct)
        sgst = cls.calculate_tax(pc_value, sgst_pct)
        total_tax = cgst + sgst
        gross_value = pc_value + total_tax
        retention_value = cls.calculate_retention(pc_value, retention_pct)
        
        return {
            "pc_value": cls.round(pc_value),
            "cgst": cgst,
            "sgst": sgst,
            "gross_value": gross_value,
            "retention_value": retention_value,
            "net_payable": gross_value - retention_value
        }
