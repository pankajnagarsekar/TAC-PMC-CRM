// AUTH CONTEXT
// Provides authentication state and methods throughout the app

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApi, baseApiClient } from '../services/apiClient';
import { User, LoginRequest } from '../types/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface LogoutCheckResult {
  can_logout: boolean;
  reason?: string;
  message?: string;
  has_draft?: boolean;
}

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  checkCanLogout: () => Promise<LogoutCheckResult>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const checkAuthStatus = useCallback(async () => {
    if (__DEV__) console.log('[Auth] Checking authentication status on app launch...');
    try {
      const isAuth = await authApi.isAuthenticated();
      if (isAuth) {
        const user = await authApi.getCurrentUser();
        if (user) {
          setState({
            user,
            isLoading: false,
            isAuthenticated: true,
          });
          if (__DEV__) console.log('[Auth] User session restored:', user.user_id);
        } else {
          // Token exists but user data missing
          console.warn('[Auth] Token exists but user data unavailable');
          setState({
            user: null,
            isLoading: false,
            isAuthenticated: false,
          });
        }
      } else {
        setState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
        });
        if (__DEV__) console.log('[Auth] No existing session found');
      }
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.error('[Auth] Session check failed:', error.message);
      } else {
        console.error('[Auth] Session check failed:', String(error));
      }
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus();

    // Listen for session invalidation from API client (BUG-20)
    baseApiClient.onSessionInvalidated = () => {
      if (__DEV__) console.log('[Auth] Session invalidated by API client — resetting state');
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      });
    };

    return () => {
      baseApiClient.onSessionInvalidated = null;
    };
  }, [checkAuthStatus]);

  const login = useCallback(async (credentials: LoginRequest): Promise<User> => {
    setState((prev: AuthState) => ({ ...prev, isLoading: true }));
    try {
      if (__DEV__) console.log('[Auth] Login attempt for user:', credentials.email);
      const response = await authApi.login(credentials);
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
      });
      console.log('[Auth] Login successful for user:', response.user.user_id);
      return response.user;
    } catch (error: unknown) {
      let errorMessage = 'Login failed';
      if (error instanceof Error) {
        errorMessage = error.message;
        console.error('[Auth] Login failed:', error.message);
      } else {
        console.error('[Auth] Login failed:', String(error));
      }
      setState((prev: AuthState) => ({ ...prev, isLoading: false }));
      throw new Error(errorMessage);
    }
  }, []);

  const logout = useCallback(async () => {
    setState((prev: AuthState) => ({ ...prev, isLoading: true }));

    try {
      if (__DEV__) console.log('[Auth] Logout initiated');
      await authApi.logout();
      console.log('[Auth] Logout completed successfully');
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.error('[Auth] Logout error:', error.message);
      } else {
        console.error('[Auth] Logout error:', String(error));
      }
      // Continue with local cleanup even if server logout fails
    } finally {
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, []);

  const checkCanLogout = useCallback(async (): Promise<LogoutCheckResult> => {
    try {
      const response = await authApi.checkCanLogout();
      return response;
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.warn('[Auth] Failed to check logout status:', error.message);
      } else {
        console.warn('[Auth] Failed to check logout status:', String(error));
      }
      // On error, allow logout (fail-safe)
      return { can_logout: true };
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const user = await authApi.getCurrentUser();
    setState((prev: AuthState) => ({ ...prev, user }));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        refreshUser,
        checkCanLogout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
