'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './AuthProvider';

interface ProtectedRouteProps {
  children: ReactNode;
  fallback?: ReactNode;
  redirectTo?: string;
}

/**
 * Protected route wrapper that redirects unauthenticated users.
 */
export function ProtectedRoute({ 
  children, 
  fallback,
  redirectTo = '/login' 
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Store the current path to redirect back after login
      const currentPath = window.location.pathname;
      if (currentPath !== redirectTo) {
        sessionStorage.setItem('redirect_after_login', currentPath);
      }
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  // Show loading state
  if (isLoading) {
    return fallback || <LoadingScreen />;
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return fallback || <LoadingScreen />;
  }

  return <>{children}</>;
}

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

export default ProtectedRoute;
