/**
 * Feature Flags Configuration
 *
 * Controls optional features that can be enabled/disabled at runtime.
 * Useful for enterprise features that require paid licenses.
 */

export const features = {
  /**
   * AG Grid Enterprise features
   * Enable: Set NEXT_PUBLIC_AG_GRID_ENTERPRISE=true in .env.local
   *
   * Features that require enterprise license:
   * - Copy/paste range selection
   * - Advanced grouping
   * - Excel export
   * - Custom cell renderers
   */
  agGridEnterprise: process.env.NEXT_PUBLIC_AG_GRID_ENTERPRISE === "true",

  /**
   * Enable advanced reporting features
   * Set NEXT_PUBLIC_ADVANCED_REPORTING=true in .env.local
   */
  advancedReporting: process.env.NEXT_PUBLIC_ADVANCED_REPORTING === "true",

  /**
   * Enable AI/ML features
   * Set NEXT_PUBLIC_AI_FEATURES=true in .env.local
   */
  aiFeatures: process.env.NEXT_PUBLIC_AI_FEATURES === "true",
} as const;

export type FeatureFlags = typeof features;

/**
 * Helper to check if enterprise features are enabled
 */
export function isEnterprise(): boolean {
  return features.agGridEnterprise;
}
