/**
 * Financial Formatting Utilities
 * Standardizes currency and percentage display across the app.
 */

/**
 * Normalizes a number to prevent -0 and NaN display.
 * Returns 0 if value is NaN or very close to zero.
 */
export function normalizeFinancial(value: number | undefined | null): number {
    if (value === undefined || value === null || isNaN(value)) return 0;
    // Handle -0 and floating point precision near zero
    return Math.abs(value) < 0.0001 ? 0 : value;
}

/**
 * Formats a currency value for India (INR) with safety guards
 */
export function formatCurrencySafe(value: number | undefined | null): string {
    const normalized = normalizeFinancial(value);
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(normalized);
}

/**
 * Formats a percentage value with safety guards
 */
export function formatPercentSafe(value: number | undefined | null, decimals = 0): string {
    const normalized = normalizeFinancial(value);
    return `${normalized.toFixed(decimals)}%`;
}
/**
 * Formats a currency value for India (INR) in short form (K, L, Cr)
 */
export function formatINRShort(value: number | undefined | null): string {
    const normalized = normalizeFinancial(value);
    if (normalized >= 10000000) return `₹${(normalized / 10000000).toFixed(1)} Cr`;
    if (normalized >= 100000) return `₹${(normalized / 100000).toFixed(1)} L`;
    if (normalized >= 1000) return `₹${(normalized / 1000).toFixed(0)}K`;
    return `₹${normalized.toFixed(0)}`;
}

/**
 * Sanitizes text returned from AI models.
 * Replaces escaped newlines with actual newlines and 
 * converts dollar signs ($) to rupee symbols (₹) for currency consistency.
 */
export function sanitizeAIText(text: string | undefined | null): string {
    if (!text) return "";
    return text
        .replace(/\\n/g, '\n')
        .replace(/\$/g, '₹');
}

/**
 * Indian currency formatter for grids
 */
export function formatINR(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const rawNum = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(rawNum)) return "";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(rawNum);
}

