"""
Comprehensive financial calculations tests.
Tests: Decimal128 round-trip, tax/retention, edge cases, precision.
"""
import pytest
from decimal import Decimal
from bson import Decimal128
from app.modules.shared.domain.financial_engine import FinancialEngine


class TestDecimal128RoundTrip:
    """Test Decimal128 conversion round-trip consistency"""

    def test_round_trip_zero(self):
        """Zero should round-trip correctly"""
        value = Decimal("0.00")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("0.00")

    def test_round_trip_whole_number(self):
        """Whole numbers should round-trip correctly"""
        value = Decimal("100.00")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("100.00")

    def test_round_trip_two_decimals(self):
        """Two decimal places should round-trip correctly"""
        value = Decimal("123.45")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("123.45")

    def test_round_trip_edge_case_005(self):
        """Edge case: 0.005 (ROUND_HALF_UP should round to 0.01)"""
        value = Decimal("0.005")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        # ROUND_HALF_UP: 0.005 -> 0.01
        assert result == Decimal("0.01")

    def test_round_trip_edge_case_0045(self):
        """Edge case: 0.0045 (should round down to 0.00)"""
        value = Decimal("0.0045")
        rounded = FinancialEngine.round(value)
        d128 = FinancialEngine.to_d128(rounded)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("0.00")

    def test_round_trip_large_number(self):
        """Large numbers should round-trip correctly"""
        value = Decimal("999999.99")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("999999.99")

    def test_round_trip_precision_edge(self):
        """Multi-decimal precision should be rounded to 2 decimals"""
        value = Decimal("123.456")  # 3 decimals
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        # Should round to 2 decimals
        assert result == Decimal("123.46")  # ROUND_HALF_UP

    def test_round_trip_negative_number(self):
        """Negative numbers should round-trip correctly"""
        value = Decimal("-50.00")
        d128 = FinancialEngine.to_d128(value)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("-50.00")

    def test_round_trip_string_input(self):
        """String input should be converted correctly"""
        value = "123.45"
        result = FinancialEngine.to_decimal(FinancialEngine.to_d128(value))
        assert result == Decimal("123.45")

    def test_round_trip_int_input(self):
        """Integer input should be converted correctly"""
        value = 100
        result = FinancialEngine.to_decimal(FinancialEngine.to_d128(value))
        assert result == Decimal("100.00")

    def test_round_trip_float_input(self):
        """Float input should be converted correctly (may have precision issues)"""
        value = 123.45
        result = FinancialEngine.to_decimal(FinancialEngine.to_d128(value))
        # Float precision issues expected, but should be close
        assert abs(result - Decimal("123.45")) < Decimal("0.01")

    def test_round_trip_none_input(self):
        """None input should default to 0.00"""
        d128 = FinancialEngine.to_d128(None)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("0.00")

    def test_round_trip_decimal128_input(self):
        """Decimal128 input should pass through correctly"""
        original = Decimal128("123.45")
        d128 = FinancialEngine.to_d128(original)
        result = FinancialEngine.to_decimal(d128)
        assert result == Decimal("123.45")


class TestTaxCalculation:
    """Test tax calculation logic"""

    def test_calculate_tax_zero(self):
        """Zero tax rate should result in zero tax"""
        amount = Decimal("100.00")
        tax = FinancialEngine.calculate_tax(amount, Decimal("0"))
        assert tax == Decimal("0.00")

    def test_calculate_tax_basic(self):
        """Basic tax calculation"""
        amount = Decimal("100.00")
        tax = FinancialEngine.calculate_tax(amount, Decimal("18"))
        assert tax == Decimal("18.00")

    def test_calculate_tax_18_5_percent(self):
        """Tax with decimal percentage"""
        amount = Decimal("100.00")
        tax = FinancialEngine.calculate_tax(amount, Decimal("18.5"))
        assert tax == Decimal("18.50")

    def test_calculate_tax_precision(self):
        """Tax calculation should maintain 2 decimal precision"""
        amount = Decimal("123.45")
        tax = FinancialEngine.calculate_tax(amount, Decimal("18"))
        # 123.45 * 0.18 = 22.221 -> rounds to 22.22
        assert tax == Decimal("22.22")

    def test_calculate_tax_rounding_up(self):
        """Tax calculation should use ROUND_HALF_UP"""
        amount = Decimal("100.00")
        tax = FinancialEngine.calculate_tax(amount, Decimal("5.5"))
        # 100 * 0.055 = 5.50
        assert tax == Decimal("5.50")

    def test_calculate_tax_rounding_edge(self):
        """Tax rounding edge case"""
        amount = Decimal("10.00")
        tax = FinancialEngine.calculate_tax(amount, Decimal("15.5"))
        # 10 * 0.155 = 1.55
        assert tax == Decimal("1.55")


class TestRetentionCalculation:
    """Test retention calculation logic"""

    def test_calculate_retention_zero(self):
        """Zero retention rate should result in zero retention"""
        amount = Decimal("100.00")
        retention = FinancialEngine.calculate_retention(amount, Decimal("0"))
        assert retention == Decimal("0.00")

    def test_calculate_retention_basic(self):
        """Basic retention calculation"""
        amount = Decimal("100.00")
        retention = FinancialEngine.calculate_retention(amount, Decimal("10"))
        assert retention == Decimal("10.00")

    def test_calculate_retention_precision(self):
        """Retention calculation should maintain 2 decimal precision"""
        amount = Decimal("123.45")
        retention = FinancialEngine.calculate_retention(amount, Decimal("5"))
        # 123.45 * 0.05 = 6.1725 -> rounds to 6.17
        assert retention == Decimal("6.17")


class TestWorkOrderFinancials:
    """Test work order financial calculation"""

    def test_wo_basic_calculation(self):
        """Basic work order calculation without tax or retention"""
        result = FinancialEngine.calculate_wo_financials(
            subtotal=Decimal("1000.00"),
            discount_value=Decimal("0.00"),
            discount_type="value",
            retention_pct=Decimal("0"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["subtotal"] == Decimal("1000.00")
        assert result["discount"] == Decimal("0.00")
        assert result["after_discount"] == Decimal("1000.00")
        assert result["cgst"] == Decimal("90.00")
        assert result["sgst"] == Decimal("90.00")
        assert result["gst_amount"] == Decimal("180.00")
        assert result["grand_total"] == Decimal("1180.00")
        assert result["retention_amount"] == Decimal("0.00")
        assert result["actual_payable"] == Decimal("1180.00")

    def test_wo_with_discount(self):
        """Work order with discount"""
        result = FinancialEngine.calculate_wo_financials(
            subtotal=Decimal("1000.00"),
            discount_value=Decimal("100.00"),
            discount_type="value",
            retention_pct=Decimal("0"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["after_discount"] == Decimal("900.00")
        assert result["cgst"] == Decimal("81.00")
        assert result["sgst"] == Decimal("81.00")
        assert result["grand_total"] == Decimal("1062.00")

    def test_wo_with_retention(self):
        """Work order with retention"""
        result = FinancialEngine.calculate_wo_financials(
            subtotal=Decimal("1000.00"),
            discount_value=Decimal("0.00"),
            discount_type="value",
            retention_pct=Decimal("5"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["retention_amount"] == Decimal("50.00")
        # actual_payable = grand_total - retention
        assert result["actual_payable"] == Decimal("1130.00")

    def test_wo_full_calculation(self):
        """Work order with discount, tax, and retention"""
        result = FinancialEngine.calculate_wo_financials(
            subtotal=Decimal("1000.00"),
            discount_value=Decimal("50.00"),
            discount_type="value",
            retention_pct=Decimal("10"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["subtotal"] == Decimal("1000.00")
        assert result["discount"] == Decimal("50.00")
        assert result["after_discount"] == Decimal("950.00")
        assert result["cgst"] == Decimal("85.50")
        assert result["sgst"] == Decimal("85.50")
        assert result["gst_amount"] == Decimal("171.00")
        assert result["grand_total"] == Decimal("1121.00")
        assert result["retention_amount"] == Decimal("95.00")
        assert result["actual_payable"] == Decimal("1026.00")


class TestPettyChashFinancials:
    """Test petty cash financial calculation"""

    def test_pc_basic_calculation(self):
        """Basic PC calculation without tax or retention"""
        result = FinancialEngine.calculate_pc_financials(
            pc_value=Decimal("1000.00"),
            retention_pct=Decimal("0"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["subtotal"] == Decimal("1000.00")
        assert result["retention_amount"] == Decimal("0.00")
        assert result["total_after_retention"] == Decimal("1000.00")
        assert result["cgst"] == Decimal("90.00")
        assert result["sgst"] == Decimal("90.00")
        assert result["gst_amount"] == Decimal("180.00")
        assert result["grand_total"] == Decimal("1180.00")

    def test_pc_with_retention(self):
        """PC with retention"""
        result = FinancialEngine.calculate_pc_financials(
            pc_value=Decimal("1000.00"),
            retention_pct=Decimal("5"),
            cgst_pct=Decimal("9"),
            sgst_pct=Decimal("9"),
        )

        assert result["retention_amount"] == Decimal("50.00")
        assert result["total_after_retention"] == Decimal("950.00")
        # GST calculated on total after retention
        assert result["cgst"] == Decimal("85.50")
        assert result["sgst"] == Decimal("85.50")
        assert result["grand_total"] == Decimal("1121.00")


class TestRounding:
    """Test rounding behavior"""

    def test_round_default_precision(self):
        """Default rounding to 2 decimals"""
        result = FinancialEngine.round(Decimal("123.456"))
        assert result == Decimal("123.46")

    def test_round_exact_half(self):
        """ROUND_HALF_UP behavior: 0.5 rounds up"""
        result = FinancialEngine.round(Decimal("123.455"))
        assert result == Decimal("123.46")

    def test_round_less_than_half(self):
        """ROUND_HALF_UP behavior: < 0.5 rounds down"""
        result = FinancialEngine.round(Decimal("123.454"))
        assert result == Decimal("123.45")

    def test_round_with_custom_precision_int(self):
        """Rounding with custom precision as integer"""
        result = FinancialEngine.round(Decimal("123.456"), precision=3)
        assert result == Decimal("123.456")

    def test_round_with_custom_precision_decimal(self):
        """Rounding with custom precision as Decimal"""
        result = FinancialEngine.round(Decimal("123.456"), precision=Decimal("0.01"))
        assert result == Decimal("123.46")

    def test_round_none_input(self):
        """None input should default to 0.00"""
        result = FinancialEngine.round(None)
        assert result == Decimal("0.00")


class TestLineItems:
    """Test line item calculation"""

    def test_line_items_basic(self):
        """Basic line item calculation"""
        result = FinancialEngine.calculate_line_items([
            {"qty": Decimal("10"), "rate": Decimal("100")},
            {"qty": Decimal("5"), "rate": Decimal("50")},
        ])

        assert len(result["items"]) == 2
        assert result["items"][0]["total"] == Decimal("1000.00")
        assert result["items"][1]["total"] == Decimal("250.00")
        assert result["subtotal"] == Decimal("1250.00")

    def test_line_items_with_precision(self):
        """Line items with decimal precision"""
        result = FinancialEngine.calculate_line_items([
            {"qty": Decimal("10.5"), "rate": Decimal("123.456")},
        ])

        item = result["items"][0]
        assert item["qty"] == Decimal("10.50")
        assert item["rate"] == Decimal("123.46")
        # 10.50 * 123.46 = 1296.33
        assert item["total"] == Decimal("1296.33")


class TestFingerprint:
    """Test fingerprint generation for integrity"""

    def test_fingerprint_consistency(self):
        """Same data should produce same fingerprint"""
        data = {"amount": Decimal("100.00"), "tax": Decimal("18.00")}
        fp1 = FinancialEngine.generate_fingerprint(data)
        fp2 = FinancialEngine.generate_fingerprint(data)
        assert fp1 == fp2

    def test_fingerprint_order_invariant(self):
        """Fingerprint should be order-invariant (uses sort_keys)"""
        data1 = {"amount": Decimal("100.00"), "tax": Decimal("18.00")}
        data2 = {"tax": Decimal("18.00"), "amount": Decimal("100.00")}
        fp1 = FinancialEngine.generate_fingerprint(data1)
        fp2 = FinancialEngine.generate_fingerprint(data2)
        assert fp1 == fp2

    def test_fingerprint_different_for_different_data(self):
        """Different data should produce different fingerprint"""
        data1 = {"amount": Decimal("100.00")}
        data2 = {"amount": Decimal("101.00")}
        fp1 = FinancialEngine.generate_fingerprint(data1)
        fp2 = FinancialEngine.generate_fingerprint(data2)
        assert fp1 != fp2


class TestIntegrityVerification:
    """Test integrity verification"""

    def test_verify_integrity_valid(self):
        """Valid checksum should verify"""
        data = {"amount": Decimal("100.00"), "tax": Decimal("18.00")}
        checksum = FinancialEngine.generate_fingerprint(data)
        assert FinancialEngine.verify_integrity(data, checksum) is True

    def test_verify_integrity_invalid(self):
        """Invalid checksum should fail verification"""
        data = {"amount": Decimal("100.00"), "tax": Decimal("18.00")}
        wrong_checksum = "wrong_hash"
        assert FinancialEngine.verify_integrity(data, wrong_checksum) is False

    def test_verify_integrity_tampered_data(self):
        """Tampered data should fail verification"""
        data = {"amount": Decimal("100.00"), "tax": Decimal("18.00")}
        checksum = FinancialEngine.generate_fingerprint(data)

        tampered = {"amount": Decimal("101.00"), "tax": Decimal("18.00")}
        assert FinancialEngine.verify_integrity(tampered, checksum) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
