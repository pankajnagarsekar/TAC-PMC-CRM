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
