'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { User } from '@/types';
import { getCurrentUser, hasStoredTokens, logout as logoutApi, storeTokens, TokenResponse } from '@/lib/auth';
import { useAuthStore } from '@/lib/store';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
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
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [isLoading, setIsLoading] = useState(true);
  const { user, isAuthenticated, setUser, logout: clearStore } = useAuthStore();

  const refreshUser = useCallback(async () => {
    try {
      // Try to get current user (works in dev mode without token)
      const userData = await getCurrentUser();
      setUser({
        id: userData.id,
        email: userData.email,
        displayName: userData.displayName,
        avatarUrl: userData.avatarUrl,
        giftedCredits: userData.giftedCredits,
        purchasedCredits: userData.purchasedCredits,
      });
    } catch (error) {
      // If no token and API call fails, clear auth state
      if (!hasStoredTokens()) {
        setUser(null);
      } else {
        // Token invalid or expired, clear auth state
        clearStore();
      }
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
      giftedCredits: userData.giftedCredits,
      purchasedCredits: userData.purchasedCredits,
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
      oauthProvider: 'google',
      giftedCredits: user.giftedCredits,
      purchasedCredits: user.purchasedCredits,
      language: 'en',
      timezone: 'UTC',
      createdAt: '',
    } : null,
    isAuthenticated,
    isLoading,
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
