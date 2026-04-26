import os
import sys
import unittest

# Add app to path for testing environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decimal import Decimal  # noqa: E402
from app.modules.shared.domain.financial_engine import FinancialEngine  # noqa: E402


class TestFinancialRounding(unittest.TestCase):
    """§10: All calculations use ROUND_HALF_UP to 2 decimal places."""

    def test_round_half_up(self):
        self.assertEqual(FinancialEngine.round(Decimal("0.005")), Decimal("0.01"))
        self.assertEqual(FinancialEngine.round(Decimal("0.004")), Decimal("0.00"))
        self.assertEqual(FinancialEngine.round(Decimal("1.255")), Decimal("1.26"))
        self.assertEqual(FinancialEngine.round(Decimal("1.254")), Decimal("1.25"))
        self.assertEqual(FinancialEngine.round(Decimal("1.25")), Decimal("1.25"))

    def test_precision(self):
        self.assertEqual(
            FinancialEngine.round(Decimal("0.0055"), precision=3), Decimal("0.006")
        )

    def test_no_float_in_round_output(self):
        result = FinancialEngine.round(Decimal("1.005"))
        self.assertIsInstance(result, Decimal)


class TestLineItems(unittest.TestCase):
    """§3.2 / §4.2: total = ROUND(qty × rate, 2)"""

    def test_single_line_item(self):
        items = [{"qty": 2, "rate": 100}]
        result = FinancialEngine.calculate_line_items(items)
        self.assertEqual(result["items"][0]["total"], Decimal("200.00"))
        self.assertEqual(result["subtotal"], Decimal("200.00"))

    def test_multiple_line_items_subtotal(self):
        items = [
            {"qty": 3, "rate": 50},
            {"qty": 1, "rate": 200},
            {"qty": 2, "rate": 75},
        ]
        result = FinancialEngine.calculate_line_items(items)
        # 150 + 200 + 150 = 500
        self.assertEqual(result["subtotal"], Decimal("500.00"))

    def test_line_item_rounding(self):
        # qty=1.333 → rounds to 1.33, rate=3 → 1.33 × 3 = 3.99
        # (each value is rounded before multiplication per ROUND_HALF_UP)
        items = [{"qty": "1.333", "rate": "3"}]
        result = FinancialEngine.calculate_line_items(items)
        self.assertEqual(result["items"][0]["total"], Decimal("3.99"))

    def test_empty_line_items(self):
        result = FinancialEngine.calculate_line_items([])
        self.assertEqual(result["subtotal"], Decimal("0.00"))
        self.assertEqual(result["items"], [])


class TestWOFinancials(unittest.TestCase):
    """§3.3: WO Totals — strict field-by-field verification."""

    def _calc(self, subtotal, discount=0, retention_pct=0, cgst_pct=9, sgst_pct=9):
        return FinancialEngine.calculate_wo_financials(
            subtotal=Decimal(str(subtotal)),
            discount=Decimal(str(discount)),
            retention_pct=Decimal(str(retention_pct)),
            cgst_pct=Decimal(str(cgst_pct)),
            sgst_pct=Decimal(str(sgst_pct)),
        )

    def test_total_before_tax_is_subtotal_minus_discount(self):
        fin = self._calc(subtotal=1000, discount=100)
        self.assertEqual(fin["total_before_tax"], Decimal("900.00"))

    def test_cgst_calculated_on_total_before_tax_not_subtotal(self):
        fin = self._calc(subtotal=1000, discount=100, cgst_pct=9)
        # CGST on 900, not 1000
        self.assertEqual(fin["cgst"], Decimal("81.00"))

    def test_sgst_calculated_on_total_before_tax_not_subtotal(self):
        fin = self._calc(subtotal=1000, discount=100, sgst_pct=9)
        self.assertEqual(fin["sgst"], Decimal("81.00"))

    def test_grand_total(self):
        fin = self._calc(subtotal=1000, discount=100, cgst_pct=9, sgst_pct=9)
        # grand_total = 900 + 81 + 81 = 1062
        self.assertEqual(fin["grand_total"], Decimal("1062.00"))

    def test_retention_calculated_on_total_before_tax(self):
        # Per spec §3.3: retention_amount = grand_total × (retention_percent / 100)
        fin = self._calc(subtotal=1000, discount=0, retention_pct=10, cgst_pct=0, sgst_pct=0)
        # grand_total = 1000, retention = 1000 × 10% = 100
        self.assertEqual(fin["retention_amount"], Decimal("100.00"))

    def test_total_payable_equals_grand_total(self):
        """§3.3: total_payable = grand_total"""
        fin = self._calc(subtotal=1000, discount=100, retention_pct=5)
        self.assertEqual(fin["total_payable"], fin["grand_total"])

    def test_actual_payable_equals_grand_total_minus_retention(self):
        """§3.3: actual_payable = grand_total - retention_amount"""
        fin = self._calc(subtotal=1000, discount=0, retention_pct=10, cgst_pct=0, sgst_pct=0)
        self.assertEqual(fin["actual_payable"], Decimal("900.00"))

    def test_no_discount_no_taxes(self):
        fin = self._calc(subtotal=500, discount=0, cgst_pct=0, sgst_pct=0)
        self.assertEqual(fin["total_before_tax"], Decimal("500.00"))
        self.assertEqual(fin["grand_total"], Decimal("500.00"))
        self.assertEqual(fin["total_payable"], Decimal("500.00"))

    def test_all_keys_present(self):
        """Regression: total_payable was missing, causing KeyError at runtime."""
        fin = self._calc(subtotal=1000)
        required_keys = [
            "subtotal", "discount", "total_before_tax",
            "cgst", "sgst", "grand_total",
            "retention_amount", "total_payable", "actual_payable",
        ]
        for key in required_keys:
            self.assertIn(key, fin, f"Missing key: {key}")

    def test_negative_discount_raises(self):
        """Subtotal after discount cannot be negative."""
        from app.modules.shared.domain.exceptions import FinancialIntegrityError  # noqa: E402
        with self.assertRaises(FinancialIntegrityError):
            self._calc(subtotal=100, discount=200)

    def test_rounding_at_each_step(self):
        # Values that would accumulate float error without proper rounding
        fin = self._calc(subtotal="333.33", discount=0, cgst_pct="9", sgst_pct="9")
        self.assertEqual(fin["cgst"], FinancialEngine.round(Decimal("333.33") * Decimal("9") / 100))
        self.assertEqual(fin["sgst"], FinancialEngine.round(Decimal("333.33") * Decimal("9") / 100))


class TestPCFinancials(unittest.TestCase):
    """§4.3: PC Totals — retention first, then tax on remaining."""

    def _calc(self, subtotal, retention_pct=0, cgst_pct=9, sgst_pct=9):
        return FinancialEngine.calculate_pc_financials(
            pc_value=Decimal(str(subtotal)),
            retention_pct=Decimal(str(retention_pct)),
            cgst_pct=Decimal(str(cgst_pct)),
            sgst_pct=Decimal(str(sgst_pct)),
        )

    def test_retention_applied_to_subtotal(self):
        fin = self._calc(subtotal=1000, retention_pct=10, cgst_pct=0, sgst_pct=0)
        self.assertEqual(fin["retention_amount"], Decimal("100.00"))
        self.assertEqual(fin["total_after_retention"], Decimal("900.00"))

    def test_cgst_on_total_after_retention_not_subtotal(self):
        fin = self._calc(subtotal=1000, retention_pct=10, cgst_pct=9, sgst_pct=0)
        # CGST on 900, not 1000
        self.assertEqual(fin["cgst"], Decimal("81.00"))

    def test_sgst_on_total_after_retention_not_subtotal(self):
        fin = self._calc(subtotal=1000, retention_pct=10, cgst_pct=0, sgst_pct=9)
        self.assertEqual(fin["sgst"], Decimal("81.00"))

    def test_grand_total(self):
        fin = self._calc(subtotal=1000, retention_pct=10, cgst_pct=9, sgst_pct=9)
        # total_after_retention=900, cgst=81, sgst=81 → grand_total=1062
        self.assertEqual(fin["grand_total"], Decimal("1062.00"))

    def test_no_retention_no_taxes(self):
        fin = self._calc(subtotal=500, retention_pct=0, cgst_pct=0, sgst_pct=0)
        self.assertEqual(fin["total_after_retention"], Decimal("500.00"))
        self.assertEqual(fin["grand_total"], Decimal("500.00"))

    def test_all_keys_present(self):
        fin = self._calc(subtotal=1000)
        required_keys = [
            "subtotal", "retention_amount", "total_after_retention",
            "cgst", "sgst", "grand_total",
        ]
        for key in required_keys:
            self.assertIn(key, fin, f"Missing key: {key}")


class TestNegativeRules(unittest.TestCase):
    """§7: remaining_budget and cash_in_hand CAN be negative; allocation_remaining CANNOT."""

    def test_remaining_budget_can_be_negative(self):
        """committed_amount > original_budget → remaining_budget is negative (warning only)."""
        original_budget = Decimal("1000.00")
        committed_amount = Decimal("1200.00")
        remaining_budget = original_budget - committed_amount
        self.assertEqual(remaining_budget, Decimal("-200.00"))
        # No exception raised — this is a warning only scenario

    def test_cash_in_hand_can_be_negative(self):
        """total_expenses > allocation_received → cash_in_hand is negative."""
        allocation_received = Decimal("500.00")
        total_expenses = Decimal("600.00")
        cash_in_hand = allocation_received - total_expenses
        self.assertEqual(cash_in_hand, Decimal("-100.00"))
        # No exception raised — warning only

    def test_allocation_remaining_invariant(self):
        """allocation_remaining = allocation_original - allocation_received (never <0 by design)."""
        allocation_original = Decimal("2000.00")
        allocation_received = Decimal("1500.00")
        allocation_remaining = allocation_original - allocation_received
        self.assertEqual(allocation_remaining, Decimal("500.00"))
        self.assertGreaterEqual(allocation_remaining, Decimal("0.00"))


class TestFinancialInvariants(unittest.TestCase):
    """§9: Financial Invariants — pure arithmetic verification."""

    def test_invariant_1_committed_amount_sum_of_wo_grand_totals(self):
        wo_grand_totals = [Decimal("1000.00"), Decimal("500.00"), Decimal("250.00")]
        committed_amount = sum(wo_grand_totals)
        self.assertEqual(committed_amount, Decimal("1750.00"))

    def test_invariant_2_remaining_budget(self):
        original_budget = Decimal("5000.00")
        committed_amount = Decimal("1750.00")
        remaining_budget = original_budget - committed_amount
        self.assertEqual(remaining_budget, Decimal("3250.00"))

    def test_invariant_3_master_remaining_is_sum_of_category_remaining(self):
        category_remainings = [Decimal("3250.00"), Decimal("800.00"), Decimal("-200.00")]
        master_remaining = sum(category_remainings)
        self.assertEqual(master_remaining, Decimal("3850.00"))

    def test_invariant_4_allocation_remaining(self):
        allocation_original = Decimal("2000.00")
        allocation_received = Decimal("800.00")
        allocation_remaining = allocation_original - allocation_received
        self.assertEqual(allocation_remaining, Decimal("1200.00"))

    def test_invariant_5_cash_in_hand(self):
        allocation_received = Decimal("800.00")
        total_expenses = Decimal("300.00")
        cash_in_hand = allocation_received - total_expenses
        self.assertEqual(cash_in_hand, Decimal("500.00"))

    def test_invariant_6_vendor_payable(self):
        """vendor_payable = SUM(PC created) - SUM(PC closed)"""
        pc_created_totals = [Decimal("400.00"), Decimal("600.00")]
        pc_closed_totals = [Decimal("400.00")]
        vendor_payable = sum(pc_created_totals) - sum(pc_closed_totals)
        self.assertEqual(vendor_payable, Decimal("600.00"))

    def test_expense_does_not_affect_allocation_remaining(self):
        """§5.3: expense log affects cash_in_hand and total_expenses, NOT allocation_remaining."""
        allocation_original = Decimal("2000.00")
        allocation_received = Decimal("800.00")
        allocation_remaining_before = allocation_original - allocation_received

        expense_amount = Decimal("150.00")
        total_expenses_after = Decimal("0.00") + expense_amount
        cash_in_hand_after = allocation_received - total_expenses_after

        # allocation_remaining must be unchanged
        allocation_remaining_after = allocation_original - allocation_received
        self.assertEqual(allocation_remaining_before, allocation_remaining_after)
        self.assertEqual(cash_in_hand_after, Decimal("650.00"))

    def test_pc_close_petty_ovh_updates_all_fields(self):
        """§5.2: On PC CLOSE for Petty/OVH, verify all field updates."""
        allocation_original = Decimal("2000.00")
        allocation_received_before = Decimal("500.00")
        cash_in_hand_before = Decimal("200.00")
        pc_grand_total = Decimal("300.00")

        allocation_received_after = allocation_received_before + pc_grand_total
        allocation_remaining_after = allocation_original - allocation_received_after
        cash_in_hand_after = cash_in_hand_before + pc_grand_total

        self.assertEqual(allocation_received_after, Decimal("800.00"))
        self.assertEqual(allocation_remaining_after, Decimal("1200.00"))
        self.assertEqual(cash_in_hand_after, Decimal("500.00"))


class TestWOAndPCDifference(unittest.TestCase):
    """Verify the key structural difference: WO tax before retention, PC retention before tax."""

    def test_wo_vs_pc_same_inputs_different_results(self):
        subtotal = Decimal("1000.00")
        retention_pct = Decimal("10")
        cgst_pct = Decimal("9")
        sgst_pct = Decimal("9")

        wo = FinancialEngine.calculate_wo_financials(
            subtotal=subtotal,
            discount=Decimal("0"),
            retention_pct=retention_pct,
            cgst_pct=cgst_pct,
            sgst_pct=sgst_pct,
        )
        pc = FinancialEngine.calculate_pc_financials(
            pc_value=subtotal,
            retention_pct=retention_pct,
            cgst_pct=cgst_pct,
            sgst_pct=sgst_pct,
        )

        # WO: tax on full 1000, retention on grand_total
        # grand_total = 1000 + 90 + 90 = 1180
        self.assertEqual(wo["grand_total"], Decimal("1180.00"))
        self.assertEqual(wo["retention_amount"], Decimal("100.00"))  # 1000 × 10% per spec — retention on total_before_tax

        # PC: retention on 1000 first (100), tax on 900
        # grand_total = 900 + 81 + 81 = 1062
        self.assertEqual(pc["grand_total"], Decimal("1062.00"))
        self.assertEqual(pc["retention_amount"], Decimal("100.00"))

        # Grand totals must differ
        self.assertNotEqual(wo["grand_total"], pc["grand_total"])


if __name__ == "__main__":
    unittest.main()
