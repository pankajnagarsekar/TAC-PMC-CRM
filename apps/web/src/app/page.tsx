'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

// Root page — just a redirect based on auth state
export default function RootPage() {
  const router = useRouter();
  const { user, accessToken, _hasHydrated } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // Wait for hydration before checking auth
    if (!mounted || !_hasHydrated) return;

    console.log('RootPage: Auth state', { hasToken: !!accessToken, hasUser: !!user, role: user?.role });
    if (!accessToken || !user) {
      router.replace('/login');
    } else if (user.role === 'Admin') {
      router.replace('/admin/dashboard');
    } else {
      router.replace('/login');
    }
  }, [accessToken, user, router, mounted, _hasHydrated]);

  console.log('RootPage: rendering loader');

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Loading TAC-PMC CRM...</p>
      </div>
    </div>
  );
}
