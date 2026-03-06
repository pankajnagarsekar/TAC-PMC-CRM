import { v4 as uuidv4 } from 'uuid';

/**
 * Client-side idempotency handler.
 * Generates and stores unique keys for operations to prevent double-submission.
 * Keys are stored in sessionStorage to persist through page reloads but clear on tab close.
 */
export const idempotency = {
  /**
   * Get or generate an idempotency key for a specific operation.
   */
  get: (operationId: string): string => {
    const storageKey = `idempotency_${operationId}`;
    let key = sessionStorage.getItem(storageKey);
    if (!key) {
      key = uuidv4();
      sessionStorage.setItem(storageKey, key);
    }
    return key;
  },

  /**
   * Clear the key after successful operation completion.
   */
  clear: (operationId: string): void => {
    sessionStorage.removeItem(`idempotency_${operationId}`);
  }
};
