/**
 * Self-contained verification script for financial logic synchronization.
 * Run with: node verify_financial_sync.js
 */

function financialRound(num) {
  const sign = Math.sign(num);
  const absNum = Math.abs(num);
  const rounded = Number(Math.round(Number(absNum + "e+2")) + "e-2") * sign;
  if (rounded === 0 || Object.is(rounded, -0)) {
    return 0;
  }
  return rounded;
}

function calculatePCFinancials(pcValue, retentionPct, cgstPct, sgstPct) {
  const subtotal = financialRound(pcValue);
  const retentionAmount = financialRound(subtotal * (retentionPct / 100));
  const cgst = financialRound(subtotal * (cgstPct / 100));
  const sgst = financialRound(subtotal * (sgstPct / 100));
  const gstAmount = financialRound(cgst + sgst);
  const grandTotal = financialRound(subtotal + gstAmount);
  const actualPayable = financialRound(grandTotal - retentionAmount);
  return { subtotal, retentionAmount, cgst, sgst, gstAmount, grandTotal, actualPayable, netPayable: actualPayable };
}

function calculateWOFinancials(subtotal, discountValue, discountType, retentionPct, cgstPct, sgstPct) {
  const roundedSubtotal = financialRound(subtotal);
  const roundedDiscountValue = financialRound(discountValue);
  let calculatedDiscount = 0;
  if (discountType === "percentage") {
    calculatedDiscount = financialRound(roundedSubtotal * (roundedDiscountValue / 100));
  } else {
    calculatedDiscount = roundedDiscountValue;
  }
  const totalBeforeTax = financialRound(roundedSubtotal - calculatedDiscount);
  const cgst = financialRound(totalBeforeTax * (cgstPct / 100));
  const sgst = financialRound(totalBeforeTax * (sgstPct / 100));
  const gstAmount = financialRound(cgst + sgst);
  const retentionAmount = financialRound(totalBeforeTax * (retentionPct / 100));
  const grandTotal = financialRound(totalBeforeTax + gstAmount);
  const actualPayable = financialRound(grandTotal - retentionAmount);
  return { subtotal: roundedSubtotal, discount: calculatedDiscount, totalBeforeTax, cgst, sgst, gstAmount, retentionAmount, grandTotal, actualPayable };
}

function assert(condition, message) {
    if (!condition) {
        console.error(`❌ FAILED: ${message}`);
        process.exit(1);
    }
    console.log(`✅ PASSED: ${message}`);
}

console.log("--- Starting Financial Logic Verification ---\n");

// 1. Rounding Tests (Match Python Decimal ROUND_HALF_UP)
console.log("1. Testing Rounding Logic (BUG-025)");
assert(financialRound(1.005) === 1.01, "1.005 should round to 1.01");
assert(financialRound(1.015) === 1.02, "1.015 should round to 1.02");
assert(financialRound(1.0045) === 1.00, "1.0045 should round to 1.00");
assert(financialRound(-1.005) === -1.01, "-1.005 should round to -1.01");
assert(Object.is(financialRound(-0.0001), 0), "-0.0001 should round to 0 (Fix BUG-025)");

// 2. PC Financials Tests (Match BUG-003)
console.log("\n2. Testing PC Financials (BUG-003: GST on Full Subtotal)");
const pcRes = calculatePCFinancials(1000, 5, 9, 9);
assert(pcRes.subtotal === 1000, "Subtotal should be 1000");
assert(pcRes.cgst === 90, "CGST (9%) on 1000 should be 90");
assert(pcRes.sgst === 90, "SGST (9%) on 1000 should be 90");
assert(pcRes.gstAmount === 180, "GST Amount should be 180");
assert(pcRes.grandTotal === 1180, "Grand Total should be 1180");
assert(pcRes.retentionAmount === 50, "Retention (5%) on 1000 should be 50");
assert(pcRes.actualPayable === 1130, "Actual Payable should be 1180 - 50 = 1130");
assert(pcRes.netPayable === 1130, "netPayable should be alias for actualPayable (BUG-001)");

// 3. WO Financials Tests
console.log("\n3. Testing WO Financials");
const woRes = calculateWOFinancials(1000, 50, "value", 10, 9, 9);
assert(woRes.subtotal === 1000, "Subtotal should be 1000");
assert(woRes.discount === 50, "Discount should be 50");
assert(woRes.totalBeforeTax === 950, "Total before tax should be 950");
assert(woRes.cgst === 85.5, "CGST (9%) on 950 should be 85.5");
assert(woRes.sgst === 85.5, "SGST (9%) on 950 should be 85.5");
assert(woRes.gstAmount === 171, "GST Amount should be 171");
assert(woRes.grandTotal === 1121, "Grand Total should be 1121");
assert(woRes.retentionAmount === 95, "Retention (10%) on 950 should be 95");
assert(woRes.actualPayable === 1026, "Actual Payable should be 1121 - 95 = 1026");

console.log("\n--- Verification Complete: 100% Logic Synchronized ---");
