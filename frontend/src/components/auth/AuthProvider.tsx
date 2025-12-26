'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { User } from '@/types';
import { getCurrentUser, hasStoredTokens, logout as logoutApi, storeTokens, TokenResponse } from '@/lib/auth';
import { useAuthStore } from '@/lib/store';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isDevMode: boolean;
  login: (tokens: TokenResponse, user: User) => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Authentication provider component that manages auth state.
 * When DISABLE_AUTH=true on backend, authentication is bypassed entirely.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isDevMode, setIsDevMode] = useState(false);
  const { user, isAuthenticated, setUser, logout: clearStore } = useAuthStore();

  // Initialize dev mode token if enabled
  useEffect(() => {
    const devModeEnabled = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    setIsDevMode(devModeEnabled);

    if (devModeEnabled && !hasStoredTokens()) {
      console.log('[AuthProvider] Dev mode enabled - generating dev token');
      // Generate a dev token for local development
      const devToken = 'dev-token-' + Date.now();
      localStorage.setItem('access_token', devToken);
      localStorage.setItem('refresh_token', devToken);
      console.log('[AuthProvider] Dev token created:', devToken);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    // Skip user fetch if on auth pages to prevent redirect loop
    const isAuthPage = typeof window !== 'undefined' && (
      window.location.pathname === '/login' ||
      window.location.pathname === '/auth/callback' ||
      window.location.pathname === '/auth/pending'
    );

    if (isAuthPage) {
      console.log('[AuthProvider] Skipping user fetch on auth page');
      setIsLoading(false);
      return;
    }

    // Skip if no tokens are stored
    if (!hasStoredTokens()) {
      console.log('[AuthProvider] No tokens found, skipping user fetch');
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      // Try to get current user - backend handles dev mode internally
      // If DISABLE_AUTH=true, backend returns a mock user without requiring token
      const userData = await getCurrentUser();
      setUser({
        id: userData.id,
        email: userData.email,
        displayName: userData.displayName,
        avatarUrl: userData.avatarUrl,
        oauthProvider: userData.oauthProvider,
        giftedCredits: userData.giftedCredits,
        purchasedCredits: userData.purchasedCredits,
        language: userData.language,
        timezone: userData.timezone,
        conversationalProvider: userData.conversationalProvider,
        conversationalModel: userData.conversationalModel,
        isApproved: userData.isApproved,
        isSuperAdmin: userData.isSuperAdmin,
        createdAt: userData.createdAt,
        lastLoginAt: userData.lastLoginAt,
      });
    } catch (error) {
      console.error('[AuthProvider] Failed to refresh user:', error);
      // Token invalid or expired, clear auth state silently
      // Don't redirect here - let the API interceptor handle it
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [setUser, clearStore]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback((tokens: TokenResponse, userData: User) => {
    storeTokens(tokens);
    setUser({
      id: userData.id,
      email: userData.email,
      displayName: userData.displayName,
      avatarUrl: userData.avatarUrl,
      oauthProvider: userData.oauthProvider,
      giftedCredits: userData.giftedCredits,
      purchasedCredits: userData.purchasedCredits,
      language: userData.language,
      timezone: userData.timezone,
      conversationalProvider: userData.conversationalProvider,
      conversationalModel: userData.conversationalModel,
      isApproved: userData.isApproved,
      isSuperAdmin: userData.isSuperAdmin,
      createdAt: userData.createdAt,
      lastLoginAt: userData.lastLoginAt,
    });
  }, [setUser]);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } finally {
      clearStore();
    }
  }, [clearStore]);

  const value: AuthContextType = {
    user: user ? {
      id: user.id,
      email: user.email,
      displayName: user.displayName,
      avatarUrl: user.avatarUrl,
      oauthProvider: user.oauthProvider || 'google',
      giftedCredits: user.giftedCredits,
      purchasedCredits: user.purchasedCredits,
      language: user.language || 'en',
      timezone: user.timezone || 'UTC',
      conversationalProvider: user.conversationalProvider || 'gemini',
      conversationalModel: user.conversationalModel || 'gemini-2.5-flash',
      isApproved: user.isApproved || false,
      isSuperAdmin: user.isSuperAdmin || false,
      createdAt: user.createdAt || '',
      lastLoginAt: user.lastLoginAt,
    } : null,
    isAuthenticated,
    isLoading,
    isDevMode,
    login,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access authentication context.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthProvider;
