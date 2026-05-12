/**
 * Financial rounding utility to match Python's Decimal ROUND_HALF_UP logic.
 * This prevents 1-paisa drift between frontend and backend.
 */
export function financialRound(num: number): number {
  // Use scientific notation strings to avoid floating point issues during intermediate steps
  // e.g., 1.005 + "e+2" -> 100.5, Math.round(100.5) -> 101, 101 + "e-2" -> 1.01
  return Number(Math.round(Number(num + "e+2")) + "e-2");
}

/**
 * Formats a number for financial display with exactly 2 decimal places.
 */
export function formatCurrency(num: number): string {
  return financialRound(num).toFixed(2);
}

export interface PCFinancials {
  subtotal: number;
  retentionAmount: number;
  cgst: number;
  sgst: number;
  gstAmount: number;
  grandTotal: number;
  actualPayable: number;
}

/**
 * Replicates FinancialEngine.calculate_pc_financials in TypeScript
 */
export function calculatePCFinancials(
  pcValue: number,
  retentionPct: number,
  cgstPct: number,
  sgstPct: number
): PCFinancials {
  const subtotal = financialRound(pcValue);
  const retentionAmount = financialRound(subtotal * (retentionPct / 100));

  // BUG-003: GST on FULL subtotal
  const cgst = financialRound(subtotal * (cgstPct / 100));
  const sgst = financialRound(subtotal * (sgstPct / 100));
  const gstAmount = financialRound(cgst + sgst);

  // Grand Total = Gross Subtotal + GST
  const grandTotal = financialRound(subtotal + gstAmount);
  // Actual Payable = Grand Total - Retention
  const actualPayable = financialRound(grandTotal - retentionAmount);

  return {
    subtotal,
    retentionAmount,
    cgst,
    sgst,
    gstAmount,
    grandTotal,
    actualPayable,
  };
}

export interface WOFinancials {
  subtotal: number;
  discount: number;
  totalBeforeTax: number;
  cgst: number;
  sgst: number;
  gstAmount: number;
  retentionAmount: number;
  grandTotal: number;
  actualPayable: number;
}

/**
 * Replicates FinancialEngine.calculate_wo_financials in TypeScript
 */
export function calculateWOFinancials(
  subtotal: number,
  discountValue: number,
  discountType: "percentage" | "value",
  retentionPct: number,
  cgstPct: number,
  sgstPct: number
): WOFinancials {
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

  return {
    subtotal: roundedSubtotal,
    discount: calculatedDiscount,
    totalBeforeTax,
    cgst,
    sgst,
    gstAmount,
    retentionAmount,
    grandTotal,
    actualPayable,
  };
}
