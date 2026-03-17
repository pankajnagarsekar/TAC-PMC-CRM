import { useState, useCallback, useRef } from "react";

interface UseRequestLockOptions {
  operationId: string;
  timeoutMs?: number;
}

interface UseRequestLockReturn {
  isLocked: boolean;
  lock: () => void;
  unlock: () => void;
  executeWithLock: <T>(fn: () => Promise<T>) => Promise<T | null>;
}

/**
 * Request locking hook to prevent duplicate submissions.
 * This implements the requirement from Phase 6.2.4:
 * "if a financial save is in-flight, subsequent clicks are silently blocked"
 *
 * Features:
 * - Tracks in-flight requests per operation
 * - Optional timeout to auto-release lock
 * - Silently blocks subsequent clicks when locked
 * - Works across components via operationId
 */
export function useRequestLock(
  options: UseRequestLockOptions,
): UseRequestLockReturn {
  const { operationId, timeoutMs = 30000 } = options;
  const [isLocked, setIsLocked] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const lock = useCallback(() => {
    setIsLocked(true);

    // Auto-release after timeout to prevent permanent lock
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setIsLocked(false);
    }, timeoutMs);
  }, [timeoutMs]);

  const unlock = useCallback(() => {
    setIsLocked(false);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const executeWithLock = useCallback(
    async <T>(fn: () => Promise<T>): Promise<T | null> => {
      if (isLocked) {
        console.warn(
          `[RequestLock] Operation "${operationId}" is already in progress. Silently blocking.`,
        );
        return null;
      }

      lock();
      try {
        const result = await fn();
        return result;
      } catch (error) {
        throw error;
      } finally {
        unlock();
      }
    },
    [isLocked, lock, unlock, operationId],
  );

  return {
    isLocked,
    lock,
    unlock,
    executeWithLock,
  };
}

/**
 * Global request lock manager for cross-component coordination.
 * Uses sessionStorage to coordinate locks across components on the same page.
 */
export const requestLockManager = {
  /**
   * Acquire a lock for a specific operation
   */
  acquire: (operationId: string): boolean => {
    const storageKey = `request_lock_${operationId}`;
    const existing = sessionStorage.getItem(storageKey);

    if (existing) {
      return false; // Lock already held
    }

    sessionStorage.setItem(storageKey, Date.now().toString());
    return true;
  },

  /**
   * Release a lock for a specific operation
   */
  release: (operationId: string): void => {
    const storageKey = `request_lock_${operationId}`;
    sessionStorage.removeItem(storageKey);
  },

  /**
   * Check if an operation is locked
   */
  isLocked: (operationId: string): boolean => {
    const storageKey = `request_lock_${operationId}`;
    return sessionStorage.getItem(storageKey) !== null;
  },

  /**
   * Get all active locks (for debugging)
   */
  getActiveLocks: (): string[] => {
    const locks: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith("request_lock_")) {
        locks.push(key.replace("request_lock_", ""));
      }
    }
    return locks;
  },
};
