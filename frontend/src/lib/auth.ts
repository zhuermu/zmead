/**
 * Authentication API functions and utilities.
 */

import api from './api';
import { User } from '@/types';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  tokens: TokenResponse;
  user: UserApiResponse;
}

export interface UserApiResponse {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string | null;
  oauth_provider: string;
  gifted_credits: number;
  purchased_credits: number;
  total_credits: number;
  language: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

/**
 * Convert API user response to frontend User type.
 */
export function mapUserResponse(apiUser: UserApiResponse): User {
  return {
    id: apiUser.id,
    email: apiUser.email,
    displayName: apiUser.display_name,
    avatarUrl: apiUser.avatar_url ?? undefined,
    oauthProvider: apiUser.oauth_provider,
    giftedCredits: apiUser.gifted_credits,
    purchasedCredits: apiUser.purchased_credits,
    language: apiUser.language,
    timezone: apiUser.timezone,
    createdAt: apiUser.created_at,
    lastLoginAt: apiUser.last_login_at ?? undefined,
  };
}

/**
 * Get Google OAuth URL for login.
 */
export async function getGoogleOAuthUrl(state?: string): Promise<string> {
  const params = state ? `?state=${encodeURIComponent(state)}` : '';
  const response = await api.get<{ url: string }>(`/auth/oauth/google/url${params}`);
  return response.data.url;
}

/**
 * Handle OAuth callback with authorization code.
 */
export async function handleOAuthCallback(code: string, state?: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/oauth/callback', {
    code,
    state,
  });
  return response.data;
}

/**
 * Refresh access token using refresh token.
 */
export async function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return response.data;
}

/**
 * Get current user info.
 */
export async function getCurrentUser(): Promise<User> {
  const response = await api.get<UserApiResponse>('/auth/me');
  return mapUserResponse(response.data);
}

/**
 * Logout current user.
 */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout');
  } finally {
    // Always clear local storage even if API call fails
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

/**
 * Store authentication tokens.
 */
export function storeTokens(tokens: TokenResponse): void {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
}

/**
 * Check if user has valid tokens stored.
 */
export function hasStoredTokens(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('access_token');
}
