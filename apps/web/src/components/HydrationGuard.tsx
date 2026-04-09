'use client';

import { ReactNode } from 'react';
import { useHydrationGuard } from '@/hooks/useHydrationGuard';

interface HydrationGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Wrapper component that ensures stores are fully hydrated before rendering children
 *
 * Usage:
 * ```tsx
 * <HydrationGuard fallback={<LoadingSpinner />}>
 *   <YourComponent />
 * </HydrationGuard>
 * ```
 */
export function HydrationGuard({
  children,
  fallback = (
    <div className="flex items-center justify-center min-h-screen">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 rounded-full border-2 border-slate-700 border-t-orange-500 animate-spin" />
        <p className="text-slate-500 text-sm">Initializing...</p>
      </div>
    </div>
  ),
}: HydrationGuardProps) {
  const isReady = useHydrationGuard();

  if (!isReady) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
