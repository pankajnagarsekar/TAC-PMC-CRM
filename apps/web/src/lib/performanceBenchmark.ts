/**
 * Performance Benchmarking Utilities
 *
 * Implements Phase 6.5.3 - Target benchmarks:
 * - WO Save < 200ms
 * - PC Close < 200ms
 * - Petty Entry < 100ms
 * - Report gen < 2s
 */

export const PERFORMANCE_BENCHMARKS = {
  WORK_ORDER_SAVE: 200, // ms
  PAYMENT_CERTIFICATE_CLOSE: 200, // ms
  PETTY_CASH_ENTRY: 100, // ms
  REPORT_GENERATION: 2000, // ms
} as const;

export type OperationType = keyof typeof PERFORMANCE_BENCHMARKS;

interface PerformanceMetrics {
  operation: OperationType;
  durationMs: number;
  targetMs: number;
  passed: boolean;
  timestamp: string;
}

const performanceLog: PerformanceMetrics[] = [];

/**
 * Decorator/utility for timing operations against benchmarks
 */
export function measurePerformance<T>(
  operation: OperationType,
  fn: () => T | Promise<T>,
): T | Promise<T> {
  const startTime = performance.now();

  const result = fn();

  // Handle both sync and async
  if (result instanceof Promise) {
    return result.finally(() => {
      const durationMs = performance.now() - startTime;
      logPerformance(operation, durationMs);
    }) as T;
  } else {
    const durationMs = performance.now() - startTime;
    logPerformance(operation, durationMs);
    return result;
  }
}

/**
 * Async version of measurePerformance for await usage
 */
export async function measurePerformanceAsync<T>(
  operation: OperationType,
  fn: () => Promise<T>,
): Promise<T> {
  const startTime = performance.now();

  try {
    const result = await fn();
    return result;
  } finally {
    const durationMs = performance.now() - startTime;
    logPerformance(operation, durationMs);
  }
}

/**
 * Log performance metrics
 */
function logPerformance(operation: OperationType, durationMs: number): void {
  const targetMs = PERFORMANCE_BENCHMARKS[operation];
  const passed = durationMs <= targetMs;

  const metrics: PerformanceMetrics = {
    operation,
    durationMs: Math.round(durationMs * 100) / 100,
    targetMs,
    passed,
    timestamp: new Date().toISOString(),
  };

  performanceLog.push(metrics);

  // Log to console in development
  if (process.env.NODE_ENV === "development") {
    if (passed) {
      console.log(
        `[PERF] ${operation}: ${metrics.durationMs}ms ✓ (target: ${targetMs}ms)`,
      );
    } else {
      console.warn(
        `[PERF] ${operation}: ${metrics.durationMs}ms ✗ (target: ${targetMs}ms) - SLOW`,
      );
    }
  }
}

/**
 * Get performance history for an operation
 */
export function getPerformanceHistory(
  operation?: OperationType,
): PerformanceMetrics[] {
  if (operation) {
    return performanceLog.filter((m) => m.operation === operation);
  }
  return [...performanceLog];
}

/**
 * Get average performance for an operation
 */
export function getAveragePerformance(operation: OperationType): {
  avgMs: number;
  passRate: number;
} {
  const history = getPerformanceHistory(operation);
  if (history.length === 0) {
    return { avgMs: 0, passRate: 0 };
  }

  const avgMs =
    history.reduce((sum, m) => sum + m.durationMs, 0) / history.length;
  const passedCount = history.filter((m) => m.passed).length;
  const passRate = (passedCount / history.length) * 100;

  return {
    avgMs: Math.round(avgMs * 100) / 100,
    passRate: Math.round(passRate * 10) / 10,
  };
}

/**
 * Clear performance history (useful for testing)
 */
export function clearPerformanceHistory(): void {
  performanceLog.length = 0;
}
