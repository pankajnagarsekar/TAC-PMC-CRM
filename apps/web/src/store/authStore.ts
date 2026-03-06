import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UserResponse } from '@/types/api';

// ──────────────────────────────────────────────────────────────────────────
// Auth Store — persisted to localStorage
// ──────────────────────────────────────────────────────────────────────────
interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;

  setAuth: (user: UserResponse, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  isAdmin: () => boolean;
  isClient: () => boolean;
  isSupervisor: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      setAuth: (user, accessToken, refreshToken) => {
        // Also sync to localStorage for Axios interceptor
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', accessToken);
          localStorage.setItem('refresh_token', refreshToken);
        }
        set({ user, accessToken, refreshToken });
      },

      clearAuth: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
        set({ user: null, accessToken: null, refreshToken: null });
      },

      isAdmin: () => get().user?.role === 'Admin',
      isClient: () => get().user?.role === 'Client',
      isSupervisor: () => get().user?.role === 'Supervisor',
    }),
    {
      name: 'crm-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);
