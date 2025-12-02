import React from 'react';

export const useAuth = jest.fn(() => ({
  user: { id: 'test-user-123', email: 'test@example.com' },
  isLoading: false,
  error: null,
  login: jest.fn(),
  logout: jest.fn(),
}));

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};
