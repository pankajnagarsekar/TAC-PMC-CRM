/**
 * Standardized Error Logger for Frontend.
 * Centralizes error handling logic for future integration with monitoring services (e.g., Sentry).
 */
export const errorLogger = {
  error: (message: string, error?: any, context?: any) => {
    const errorData = {
      timestamp: new Date().toISOString(),
      message,
      error: error?.message || error,
      stack: error?.stack,
      context,
      url: typeof window !== 'undefined' ? window.location.href : 'ssr',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown'
    };

    // Console logging
    console.error(`[SECURE-CRM-ERROR] ${message}`, errorData);

    // In production, we would send this to a backend logging endpoint or Sentry
    // if (process.env.NODE_ENV === 'production') {
    //   sendToLoggingService(errorData);
    // }
  },

  warn: (message: string, context?: any) => {
    console.warn(`[SECURE-CRM-WARN] ${message}`, context);
  },

  log: (message: string, context?: any) => {
    if (process.env.NODE_ENV !== 'production') {
      console.log(`[SECURE-CRM-INFO] ${message}`, context);
    }
  }
};
