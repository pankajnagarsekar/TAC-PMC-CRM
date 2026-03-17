/**
 * Client-side Error Logger
 * Logs non-sensitive error data for debugging
 * Per Frontend Spec §8.2: Client-side error logging (non-sensitive data only)
 */

interface ErrorLogEntry {
  timestamp: string;
  type: "error" | "warning" | "info";
  message: string;
  stack?: string;
  componentStack?: string;
  url: string;
  userAgent: string;
  // Non-sensitive context only
  context?: Record<string, unknown>;
}

const LOG_STORAGE_KEY = "error_logs";
const MAX_LOGS = 100;

// Store original handlers for cleanup
let originalOnError: OnErrorEventHandlerNonNull | null = null;
let isHandlersInitialized = false;

/**
 * Sanitize error data to remove sensitive information
 * Removes: tokens, passwords, personal data, IDs
 */
function sanitizeErrorData(data: unknown): unknown {
  if (data === null || data === undefined) {
    return data;
  }

  if (typeof data === "string") {
    // Remove potential sensitive patterns
    return data
      .replace(
        /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
        "[EMAIL_REDACTED]",
      )
      .replace(/\b\d{10,}\b/g, "[ID_REDACTED]")
      .replace(/token[=:]\s*["']?[^"'\s]+["']?/gi, "token=[REDACTED]")
      .replace(/password[=:]\s*["']?[^"'\s]+["']?/gi, "password=[REDACTED]")
      .replace(
        /authorization[=:]\s*["']?[^"'\s]+["']?/gi,
        "authorization=[REDACTED]",
      );
  }

  // Check arrays BEFORE objects since arrays are typeof "object"
  if (Array.isArray(data)) {
    return data.map(sanitizeErrorData);
  }

  if (typeof data === "object" && data !== null) {
    const sanitized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(
      data as Record<string, unknown>,
    )) {
      // Skip sensitive keys
      const sensitiveKeys = [
        "password",
        "token",
        "secret",
        "apiKey",
        "api_key",
        "authorization",
        "auth",
        "cookie",
        "session",
        "email",
        "phone",
        "mobile",
        "userId",
        "user_id",
        "organisationId",
        "organisation_id",
      ];
      if (sensitiveKeys.some((sk) => key.toLowerCase().includes(sk))) {
        sanitized[key] = "[REDACTED]";
      } else {
        sanitized[key] = sanitizeErrorData(value);
      }
    }
    return sanitized;
  }

  return data;
}

/**
 * Get stored logs from localStorage
 */
function getStoredLogs(): ErrorLogEntry[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const stored = localStorage.getItem(LOG_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

/**
 * Save logs to localStorage
 */
function saveLogs(logs: ErrorLogEntry[]): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    // Keep only last MAX_LOGS
    const trimmed = logs.slice(-MAX_LOGS);
    localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(trimmed));
  } catch (e) {
    // Handle quota exceeded by clearing old logs and retrying
    if (e instanceof DOMException && e.name === "QuotaExceededError") {
      try {
        // Clear half the logs and retry
        const halfLogs = logs.slice(-Math.floor(MAX_LOGS / 2));
        localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(halfLogs));
      } catch {
        // Still failed - storage is truly unavailable
      }
    }
    // localStorage might be full or unavailable
  }
}

/**
 * Log an error
 */
export function logError(
  error: Error | string,
  context?: Record<string, unknown>,
): void {
  const errorMessage = typeof error === "string" ? error : error.message;
  const errorStack = typeof error === "string" ? undefined : error.stack;

  const entry: ErrorLogEntry = {
    timestamp: new Date().toISOString(),
    type: "error",
    message: errorMessage,
    stack: errorStack,
    url: typeof window !== "undefined" ? window.location.href : "",
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    context: context
      ? (sanitizeErrorData(context) as Record<string, unknown>)
      : undefined,
  };

  const logs = getStoredLogs();
  logs.push(entry);
  saveLogs(logs);

  // Also log to console in development
  if (process.env.NODE_ENV === "development") {
    console.error("[ErrorLogger]", entry);
  }
}

/**
 * Log a warning
 */
export function logWarning(
  message: string,
  context?: Record<string, unknown>,
): void {
  const entry: ErrorLogEntry = {
    timestamp: new Date().toISOString(),
    type: "warning",
    message,
    url: typeof window !== "undefined" ? window.location.href : "",
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    context: context
      ? (sanitizeErrorData(context) as Record<string, unknown>)
      : undefined,
  };

  const logs = getStoredLogs();
  logs.push(entry);
  saveLogs(logs);

  if (process.env.NODE_ENV === "development") {
    console.warn("[ErrorLogger]", entry);
  }
}

/**
 * Log info
 */
export function logInfo(
  message: string,
  context?: Record<string, unknown>,
): void {
  const entry: ErrorLogEntry = {
    timestamp: new Date().toISOString(),
    type: "info",
    message,
    url: typeof window !== "undefined" ? window.location.href : "",
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    context: context
      ? (sanitizeErrorData(context) as Record<string, unknown>)
      : undefined,
  };

  const logs = getStoredLogs();
  logs.push(entry);
  saveLogs(logs);

  if (process.env.NODE_ENV === "development") {
    console.info("[ErrorLogger]", entry);
  }
}

/**
 * Get all logs
 */
export function getLogs(): ErrorLogEntry[] {
  return getStoredLogs();
}

/**
 * Clear all logs
 */
export function clearLogs(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(LOG_STORAGE_KEY);
  }
}

/**
 * Export logs as JSON
 */
export function exportLogs(): string {
  return JSON.stringify(getStoredLogs(), null, 2);
}

/**
 * Download logs as file
 */
export function downloadLogs(): void {
  if (typeof window === "undefined") {
    return;
  }
  const logs = exportLogs();
  const blob = new Blob([logs], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `error-logs-${new Date().toISOString().split("T")[0]}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * React Error Boundary handler
 */
export function handleReactError(
  error: Error,
  errorInfo: { componentStack: string },
): void {
  logError(error, {
    componentStack: errorInfo.componentStack,
    source: "react-error-boundary",
  });
}

/**
 * Global error handler for window.onerror
 * Matches the OnErrorEventHandlerNonNull type signature
 */
export function handleGlobalError(
  event: Event | string,
  source?: string,
  lineno?: number,
  colno?: number,
  error?: Error,
): boolean {
  const message = typeof event === "string" ? event : "Unknown error";
  logError(error || message, {
    source: source || "",
    line: lineno || 0,
    column: colno || 0,
    type: "global-error",
  });
  return false; // Don't prevent default browser handling
}

/**
 * Unhandled promise rejection handler
 */
export function handleUnhandledRejection(event: PromiseRejectionEvent): void {
  logError(String(event.reason), {
    type: "unhandled-promise-rejection",
    reason: String(event.reason),
  });
}

/**
 * Initialize global error handlers
 */
export function initErrorHandlers(): void {
  if (typeof window === "undefined") {
    return;
  }

  // Prevent double initialization
  if (isHandlersInitialized) {
    logWarning("Error handlers already initialized, skipping");
    return;
  }

  // Store original handlers
  originalOnError = window.onerror;

  // Global error handler
  window.onerror = handleGlobalError;

  // Unhandled promise rejections
  window.addEventListener("unhandledrejection", handleUnhandledRejection);

  isHandlersInitialized = true;
  logInfo("Error handlers initialized");
}

/**
 * Cleanup global error handlers
 */
export function cleanupErrorHandlers(): void {
  if (typeof window === "undefined" || !isHandlersInitialized) {
    return;
  }

  // Restore original handlers
  if (originalOnError) {
    window.onerror = originalOnError;
  } else {
    window.onerror = null;
  }

  // Remove our listener
  window.removeEventListener("unhandledrejection", handleUnhandledRejection);

  isHandlersInitialized = false;
  logInfo("Error handlers cleaned up");
}

/**
 * API error logger
 */
export function logApiError(
  endpoint: string,
  status: number,
  response: unknown,
  requestData?: unknown,
): void {
  logError(`API Error: ${endpoint} (${status})`, {
    endpoint,
    status,
    response: sanitizeErrorData(response),
    requestData: sanitizeErrorData(requestData),
    type: "api-error",
  });
}

export default {
  logError,
  logWarning,
  logInfo,
  getLogs,
  clearLogs,
  exportLogs,
  downloadLogs,
  handleReactError,
  handleGlobalError,
  handleUnhandledRejection,
  initErrorHandlers,
  cleanupErrorHandlers,
  logApiError,
};
