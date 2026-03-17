/**
 * Idempotency Utility
 * Prevents duplicate submissions for financial operations
 * Per Frontend Spec §8.2: Request locking and idempotency
 */

import { v4 as uuidv4 } from "uuid";

// In-flight request tracking
const inFlightRequests = new Map<string, Promise<unknown>>();

// Completed request cache (for idempotency key replay)
const completedResponses = new Map<string, unknown>();

const IDEMPOTENCY_KEY_HEADER = "Idempotency-Key";
const IDEMPOTENCY_KEY_STORAGE = "idempotency_key_";

/**
 * Generate a new UUID for idempotency
 */
export function generateIdempotencyKey(): string {
  return uuidv4();
}

/**
 * Get or create an idempotency key for a specific operation
 * Stores in sessionStorage for persistence across page reloads
 */
export function getOrCreateIdempotencyKey(operationId: string): string {
  const storageKey = `${IDEMPOTENCY_KEY_STORAGE}${operationId}`;
  let key = sessionStorage.getItem(storageKey);

  if (!key) {
    key = generateIdempotencyKey();
    sessionStorage.setItem(storageKey, key);
  }

  return key;
}

/**
 * Clear idempotency key after successful operation
 */
export function clearIdempotencyKey(operationId: string): void {
  const storageKey = `${IDEMPOTENCY_KEY_STORAGE}${operationId}`;
  sessionStorage.removeItem(storageKey);
}

/**
 * Check if a request is already in flight
 * Returns the existing promise if found, null otherwise
 */
export function getInFlightRequest<T>(key: string): Promise<T> | null {
  const request = inFlightRequests.get(key);
  return request as Promise<T> | null;
}

/**
 * Track an in-flight request
 */
export function trackInFlightRequest<T>(
  key: string,
  promise: Promise<T>,
): Promise<T> {
  inFlightRequests.set(key, promise);

  // Clean up when done
  promise
    .then(() => {
      inFlightRequests.delete(key);
    })
    .catch(() => {
      inFlightRequests.delete(key);
    });

  return promise;
}

/**
 * Check if request is currently in flight
 */
export function isRequestInFlight(key: string): boolean {
  return inFlightRequests.has(key);
}

/**
 * Store completed response for idempotency replay
 */
export function storeCompletedResponse<T>(key: string, response: T): void {
  completedResponses.set(key, response);

  // Auto-expire after 24 hours
  setTimeout(
    () => {
      completedResponses.delete(key);
    },
    24 * 60 * 60 * 1000,
  );
}

/**
 * Get cached response for idempotency replay
 */
export function getCachedResponse<T>(key: string): T | null {
  return completedResponses.get(key) as T | null;
}

/**
 * Clear cached response
 */
export function clearCachedResponse(key: string): void {
  completedResponses.delete(key);
}

/**
 * Create fetch options with idempotency key header
 */
export function withIdempotencyKey(
  options: RequestInit,
  key: string,
): RequestInit {
  return {
    ...options,
    headers: {
      ...options.headers,
      [IDEMPOTENCY_KEY_HEADER]: key,
    },
  };
}

/**
 * Execute a request with idempotency protection
 * - Blocks duplicate in-flight requests
 * - Returns cached response for duplicate idempotency keys
 * - Clears key on success
 */
export async function executeWithIdempotency<T>(
  operationId: string,
  requestFn: (key: string) => Promise<T>,
  options: {
    clearOnSuccess?: boolean;
    useCache?: boolean;
  } = {},
): Promise<T> {
  const { clearOnSuccess = true, useCache = true } = options;

  const key = getOrCreateIdempotencyKey(operationId);

  // Check for cached response
  if (useCache) {
    const cached = getCachedResponse<T>(key);
    if (cached) {
      console.log(`[Idempotency] Returning cached response for ${operationId}`);
      return cached;
    }
  }

  // Check for in-flight request
  const inFlight = getInFlightRequest<T>(key);
  if (inFlight) {
    console.log(
      `[Idempotency] Request already in flight for ${operationId}, waiting...`,
    );
    return inFlight;
  }

  // Execute request
  const promise = requestFn(key);
  trackInFlightRequest(key, promise);

  try {
    const result = await promise;

    // Store for potential replay
    if (useCache) {
      storeCompletedResponse(key, result);
    }

    // Clear idempotency key on success
    if (clearOnSuccess) {
      clearIdempotencyKey(operationId);
    }

    return result;
  } catch (error) {
    // Don't clear key on error - allow retry with same key
    throw error;
  }
}

/**
 * Hook for React components to use idempotency
 */
export function useIdempotency() {
  return {
    generateKey: generateIdempotencyKey,
    getOrCreateKey: getOrCreateIdempotencyKey,
    clearKey: clearIdempotencyKey,
    execute: executeWithIdempotency,
    withHeader: withIdempotencyKey,
    isInFlight: isRequestInFlight,
  };
}

/**
 * Request locking utility for financial operations
 * Prevents multiple simultaneous submissions
 */
export class RequestLock {
  private locks = new Set<string>();

  /**
   * Acquire a lock for an operation
   * Returns true if lock acquired, false if already locked
   */
  acquire(operationId: string): boolean {
    if (this.locks.has(operationId)) {
      return false;
    }
    this.locks.add(operationId);
    return true;
  }

  /**
   * Release a lock
   */
  release(operationId: string): void {
    this.locks.delete(operationId);
  }

  /**
   * Check if operation is locked
   */
  isLocked(operationId: string): boolean {
    return this.locks.has(operationId);
  }

  /**
   * Execute with lock - automatically releases on completion
   */
  async executeWithLock<T>(
    operationId: string,
    fn: () => Promise<T>,
  ): Promise<T> {
    if (!this.acquire(operationId)) {
      throw new Error(`Operation ${operationId} is already in progress`);
    }

    try {
      return await fn();
    } finally {
      this.release(operationId);
    }
  }
}

// Global request lock instance
export const globalRequestLock = new RequestLock();

export default {
  generateIdempotencyKey,
  getOrCreateIdempotencyKey,
  clearIdempotencyKey,
  executeWithIdempotency,
  withIdempotencyKey,
  isRequestInFlight,
  RequestLock,
  globalRequestLock,
};
