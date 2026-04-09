'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useProjectStore } from '@/store/projectStore';

/**
 * Hook to ensure stores are hydrated before access
 * Returns true when both auth and project stores have completed hydration
 *
 * Usage:
 * ```typescript
 * const isReady = useHydrationGuard();
 * if (!isReady) return <LoadingSpinner />;
 * // Safe to use stores now
 * ```
 */
export const useHydrationGuard = (): boolean => {
  const [isMounted, setIsMounted] = useState(false);
  const authHydrated = useAuthStore((state) => state._hasHydrated);
  const projectHydrated = useProjectStore((state) => state._hasHydrated);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Both stores must be hydrated
  return isMounted && authHydrated && projectHydrated;
};

/**
 * Hook to check if auth store is hydrated
 */
export const useAuthHydrated = (): boolean => {
  const [isMounted, setIsMounted] = useState(false);
  const hasHydrated = useAuthStore((state) => state._hasHydrated);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  return isMounted && hasHydrated;
};

/**
 * Hook to check if project store is hydrated
 */
export const useProjectHydrated = (): boolean => {
  const [isMounted, setIsMounted] = useState(false);
  const hasHydrated = useProjectStore((state) => state._hasHydrated);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  return isMounted && hasHydrated;
};
