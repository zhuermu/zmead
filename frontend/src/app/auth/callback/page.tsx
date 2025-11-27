'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { handleOAuthCallback, mapUserResponse, storeTokens } from '@/lib/auth';
import { useAuth } from '@/components/auth';

function OAuthCallbackContent() {
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');

      // Handle OAuth error
      if (errorParam) {
        setError(`Authentication failed: ${errorParam}`);
        return;
      }

      // Validate code exists
      if (!code) {
        setError('No authorization code received');
        return;
      }

      // Validate state for CSRF protection
      const storedState = sessionStorage.getItem('oauth_state');
      if (state && storedState && state !== storedState) {
        setError('Invalid state parameter - possible CSRF attack');
        return;
      }
      sessionStorage.removeItem('oauth_state');

      try {
        // Exchange code for tokens
        const authResponse = await handleOAuthCallback(code, state || undefined);
        
        // Store tokens and update auth state
        storeTokens(authResponse.tokens);
        const user = mapUserResponse(authResponse.user);
        login(authResponse.tokens, user);

        // Redirect to intended destination or dashboard
        const redirectPath = sessionStorage.getItem('redirect_after_login') || '/dashboard';
        sessionStorage.removeItem('redirect_after_login');
        router.push(redirectPath);
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('Failed to complete authentication. Please try again.');
      }
    };

    processCallback();
  }, [searchParams, router, login]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
              <svg
                className="w-8 h-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              Authentication Failed
            </h1>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={() => router.push('/login')}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        <p className="text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
}

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <OAuthCallbackContent />
    </Suspense>
  );
}
