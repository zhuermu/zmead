/**
 * Application configuration.
 * API requests are proxied through Next.js rewrites to avoid CORS issues.
 */

export const config = {
  // Use relative paths - proxied through Next.js rewrites
  apiUrl: '/api/v1',
  wsUrl: typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
    : '/ws',
  appName: 'AAE Web Platform',
} as const;

export default config;
