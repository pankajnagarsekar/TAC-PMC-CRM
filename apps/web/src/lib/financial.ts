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

/**
 * Interface matching the backend's calculate_pc_financials logic
 */
export interface PCFinancials {
  subtotal: number;
  retentionAmount: number;
  totalAfterRetention: number;
  cgst: number;
  sgst: number;
  gstAmount: number;
  grandTotal: number;
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
  const totalAfterRetention = financialRound(subtotal - retentionAmount);
  
  const cgst = financialRound(totalAfterRetention * (cgstPct / 100));
  const sgst = financialRound(totalAfterRetention * (sgstPct / 100));
  const gstAmount = financialRound(cgst + sgst);
  const grandTotal = financialRound(totalAfterRetention + gstAmount);

  return {
    subtotal,
    retentionAmount,
    totalAfterRetention,
    cgst,
    sgst,
    gstAmount,
    grandTotal
  };
}
